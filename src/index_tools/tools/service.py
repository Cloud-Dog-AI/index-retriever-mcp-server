# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import asyncio
import fnmatch
import json
import mimetypes
import os
import re
import threading
import time
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any, ClassVar
from urllib.parse import unquote, urlparse
from uuid import uuid4

from cloud_dog_logging import get_logger
from cloud_dog_vdb.lifecycle.manager import mark_deleted, mark_superseded
from cloud_dog_vdb.metadata.filters import SCALAR_FILTER_FIELDS, matches_metadata
from cloud_dog_vdb.metadata.identity import compute_content_hash, normalise_source_uri
from cloud_dog_vdb.metadata.provenance import merge_provenance
from cloud_dog_vdb.metadata.schema import validate_metadata
from cloud_dog_storage import path_utils

from index_tools.audit.logger import AuditLogger
from index_tools.embeddings.adapter import EmbeddingAdapter
from index_tools.pipeline.chunking import token_chunks
from index_tools.pipeline.metadata import build_metadata
from index_tools.queue.engine import JobCancelledError, QueueEngine
from index_tools.queue.models import JobRecord, JobStatus

logger = get_logger(__name__)
from index_tools.config.loader import runtime_env_files

try:
    from cloud_dog_config import load_config
except ImportError:  # pragma: no cover
    load_config = None  # type: ignore[assignment]

_RUNTIME_TREE_CACHE: dict[str, Any] | None = None


def _cfg_val(key: str, default: Any) -> Any:
    """Read a config value via cloud_dog_config.get_config (PS-75 JQ1)."""
    try:
        from cloud_dog_config import get_config
        val = get_config(key)
        return val if val is not None else default
    except Exception:
        return default


def _run_async_blocking(coro: Any) -> Any:
    """Run a coroutine from sync tool code, including inside an active loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["value"] = loop.run_until_complete(coro)
        except BaseException as exc:  # noqa: BLE001
            result["error"] = exc
        finally:
            loop.close()

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in result:
        raise result["error"]
    return result.get("value")

try:
    from cloud_dog_idam import APIKeyManager, GroupService, UserService
    from cloud_dog_idam.domain.enums import UserStatus as IDAMUserStatus
    from cloud_dog_idam.domain.models import Group as IDAMGroup
    from cloud_dog_idam.domain.models import User as IDAMUser
except ImportError:  # pragma: no cover
    APIKeyManager = None  # type: ignore[assignment]
    GroupService = None  # type: ignore[assignment]
    UserService = None  # type: ignore[assignment]
    IDAMUserStatus = None  # type: ignore[assignment]
    IDAMGroup = None  # type: ignore[assignment]
    IDAMUser = None  # type: ignore[assignment]

try:
    from cloud_dog_vdb import CollectionSpec, ParserIngestionOptions, Record, SearchRequest, get_vdb_client, ingest_document
    from cloud_dog_vdb.capabilities.planner import plan_search as vdb_plan_search
    from cloud_dog_vdb.domain.models import CapabilityDescriptor
    from cloud_dog_vdb.ingestion.ocr.planner import decide_ocr
    from cloud_dog_vdb.ingestion.pipeline import build_parser_registry
except ImportError:  # pragma: no cover
    CollectionSpec = None  # type: ignore[assignment]
    ParserIngestionOptions = None  # type: ignore[assignment]
    Record = None  # type: ignore[assignment]
    SearchRequest = None  # type: ignore[assignment]
    CapabilityDescriptor = None  # type: ignore[assignment]
    get_vdb_client = None  # type: ignore[assignment]
    vdb_plan_search = None
    ingest_document = None
    decide_ocr = None
    build_parser_registry = None

try:
    from cloud_dog_llm import get_llm_client
except ImportError:  # pragma: no cover
    get_llm_client = None  # type: ignore[assignment]


_SECRET_FIELD_PATTERN = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*([^\s,;]+)")
_PROTECTED_METADATA_FIELDS = frozenset(
    {
        "doc_id",
        "record_id",
        "chunk_id",
        "chunk_index",
        "is_latest",
        "tenant_id",
        "namespace",
        "source",
        "source_uri",
        "source_type",
        "filename",
        "mime_type",
        "size",
        "size_bytes",
        "content_hash",
        "source_hash",
        "created_at",
        "ingested_at",
        "modified_at",
        "lifecycle_state",
        "profile",
        "collection",
        "embedding_model",
        "chunker",
        "chunker_version",
        "collection_id",
        "token_count",
        "dataset_id",
        "document_id",
        "embedding_dimensions",
        "embedding_version",
        "index_family",
        "index_record_id",
        "index_version",
        "normalisation_version",
        "pipeline_version",
        "status",
        "parser_name",
        "parser_version",
        "parser_provider",
        "ocr_provider",
        "ocr_engine",
        "ocr_confidence",
        "ocr_applied",
        "page",
        "page_number",
        "table_id",
        "chunk_kind",
        "extras",
    }
)


def _redact_diagnostic_detail(text: str) -> str:
    return _SECRET_FIELD_PATTERN.sub(r"\1=[REDACTED]", text)


def _descriptor_to_dict(descriptor: Any) -> dict[str, Any]:
    names = getattr(type(descriptor), "__dataclass_fields__", {})
    return {name: getattr(descriptor, name) for name in names}


def _infer_filename(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    candidate = parsed.path if parsed.scheme else source_uri
    return path_utils.name(unquote(candidate)) or source_uri


def _infer_mime_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "text/plain"


def _merge_document_metadata(
    base_metadata: dict[str, Any],
    override_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    document_metadata = dict(base_metadata)
    if not isinstance(override_metadata, dict):
        return document_metadata

    extras = dict(document_metadata.get("extras", {}))
    for key, value in override_metadata.items():
        if key in _PROTECTED_METADATA_FIELDS and value != base_metadata.get(key):
            extras[f"user_{key}"] = value
            continue
        document_metadata[key] = value
    if extras:
        document_metadata["extras"] = extras
    return document_metadata


def _apply_metadata_pack_aliases(metadata: dict[str, Any]) -> dict[str, Any]:
    """Mirror the archived metadata-pack field names onto the active contract."""
    doc_id = str(metadata.get("doc_id", ""))
    record_id = str(metadata.get("record_id", doc_id))
    profile = str(metadata.get("profile") or metadata.get("tenant_id") or "")
    collection = str(metadata.get("collection") or "")
    lifecycle_state = str(metadata.get("lifecycle_state", "active"))
    chunker = str(metadata.get("chunker") or "token_chunks")
    chunker_version = str(metadata.get("chunker_version") or "v1")

    metadata["document_id"] = doc_id
    metadata["index_record_id"] = record_id
    metadata["dataset_id"] = str(metadata.get("dataset_id") or profile)
    metadata["collection_id"] = str(metadata.get("collection_id") or collection)
    metadata["status"] = lifecycle_state
    metadata.setdefault("updated_at", metadata.get("modified_at") or metadata.get("created_at"))
    metadata.setdefault("language", "und")
    metadata.setdefault("title", metadata.get("filename") or metadata.get("source_uri") or doc_id)
    metadata.setdefault("authoritative_source", False)
    metadata["embedding_dimensions"] = metadata.get("embedding_dim")
    metadata.setdefault("embedding_version", metadata.get("embedding_model") or "")
    metadata["chunking_strategy"] = chunker
    metadata["pipeline_version"] = chunker_version
    metadata.setdefault("normalisation_version", "v1")
    metadata.setdefault("index_version", chunker_version)
    metadata.setdefault("index_family", "index-retriever")
    metadata.setdefault("visibility", "tenant")
    metadata.setdefault("access_scope", profile or "default")
    metadata.setdefault("retention_class", None)
    return metadata


def _metadata_compare_value(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
    return value


def _metadata_operator_match(actual: Any, expected: dict[str, Any]) -> bool:
    if actual is None:
        return False
    actual_value = _metadata_compare_value(actual)
    for operator, raw_expected in expected.items():
        expected_value = _metadata_compare_value(raw_expected)
        if operator in {"eq", "$eq"}:
            if actual_value != expected_value:
                return False
            continue
        if operator in {"ne", "$ne"}:
            if actual_value == expected_value:
                return False
            continue
        if operator in {"gte", "$gte"}:
            if actual_value < expected_value:
                return False
            continue
        if operator in {"gt", "$gt"}:
            if actual_value <= expected_value:
                return False
            continue
        if operator in {"lte", "$lte"}:
            if actual_value > expected_value:
                return False
            continue
        if operator in {"lt", "$lt"}:
            if actual_value >= expected_value:
                return False
            continue
        if operator in {"in", "$in"}:
            if not isinstance(raw_expected, (list, tuple, set)) or actual_value not in raw_expected:
                return False
            continue
        return False
    return True


def _normalise_provenance_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    normalised = dict(metadata)
    normalised.setdefault("parser_provider", "")
    normalised.setdefault("parser_version", "")
    normalised.setdefault("ocr_engine", str(normalised.get("ocr_provider", "") or ""))
    normalised.setdefault("ocr_confidence", None)
    page_value = normalised.get("page", normalised.get("page_number"))
    normalised.setdefault("page", page_value)
    normalised.setdefault("page_number", page_value)
    normalised.setdefault("table_id", "")
    normalised.setdefault("chunk_kind", str(normalised.get("chunk_kind", "") or ""))
    return normalised


def _as_plain_data(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {k: _as_plain_data(v) for k, v in value.items()}
    if isinstance(value, dict):
        return {k: _as_plain_data(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_as_plain_data(v) for v in value]
    if isinstance(value, list):
        return [_as_plain_data(v) for v in value]
    return value


def _nested_mapping(root: dict[str, Any], *keys: str) -> dict[str, Any]:
    current: Any = root
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _load_runtime_tree() -> dict[str, Any]:
    global _RUNTIME_TREE_CACHE
    if _RUNTIME_TREE_CACHE is not None:
        return _RUNTIME_TREE_CACHE
    if load_config is None:
        return {}
    try:
        compiled = load_config(
            env_files=runtime_env_files(),
            defaults_yaml="defaults.yaml",
            unresolved_policy="strict",
            vault_enabled=True,
        )
    except Exception:
        try:
            compiled = load_config(
                env_files=runtime_env_files(),
                defaults_yaml="defaults.yaml",
                unresolved_policy="empty",
                vault_enabled=False,
            )
        except Exception:
            _RUNTIME_TREE_CACHE = {}
            return _RUNTIME_TREE_CACHE
    _RUNTIME_TREE_CACHE = _as_plain_data(compiled.data)
    return _RUNTIME_TREE_CACHE


def _lookup_runtime_tree(path: str) -> Any:
    """Resolve a dotted path from the cached runtime tree."""
    current: Any = _load_runtime_tree()
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


def _resolve_env_tier(runtime_tree: dict[str, Any]) -> str:
    test_block = runtime_tree.get("test", {})
    if isinstance(test_block, dict):
        configured = str(test_block.get("env_tier", "")).strip().upper()
        if configured:
            return configured
    for env_file in runtime_env_files():
        name = path_utils.name(str(env_file)).upper()
        if name.startswith("ENV-"):
            remainder = name.removeprefix("ENV-")
            candidate = remainder.split("-", 1)[0].strip()
            if candidate:
                return candidate
    return ""


def _safe_backend_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "default"


class ProviderDiagnosticError(ValueError):
    """ProviderDiagnosticError definition."""

    def __init__(
        self,
        *,
        operation: str,
        provider: str,
        message: str,
        detail: str,
    ) -> None:
        envelope = {
            "error": {
                "code": "PROVIDER_DIAGNOSTIC",
                "operation": operation,
                "provider": provider,
                "message": message,
                "detail": _redact_diagnostic_detail(detail),
            }
        }
        super().__init__(json.dumps(envelope, ensure_ascii=True, sort_keys=True))
        self.envelope = envelope


@dataclass(slots=True)
class _PreviewResult:
    record_ids: list[str]
    metadata: dict[str, Any]
    chunks: list[str]
    checkpoints: list[dict[str, Any]]


class _PreviewVdbBridge:
    """Preview bridge that captures records written by cloud_dog_vdb ingestion."""

    def __init__(self) -> None:
        self.records: list[Any] = []

    async def upsert_records(  # noqa: D401 - async surface must match cloud_dog_vdb client
        self,
        collection: str,
        records: list[Any],
        provider_id: str | None = None,
    ) -> list[str]:
        _ = collection, provider_id
        self.records.extend(records)
        return [str(record.record_id) for record in records]


@dataclass(slots=True)
class DocumentRecord:
    """DocumentRecord definition."""

    doc_id: str
    profile: str
    collection: str
    source: str
    text: str
    metadata: dict[str, Any]
    created_at: datetime
    record_id: str = ""


@dataclass(slots=True)
class StreamSession:
    """StreamSession definition."""

    session_id: str
    profile: str
    collection: str
    ordering_key: str
    closed: bool = False
    ingested_events: int = 0
    job_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UserRecord:
    """UserRecord definition."""

    user_id: str
    display_name: str
    roles: set[str]
    groups: set[str] = field(default_factory=set)
    enabled: bool = True


@dataclass(slots=True)
class GroupRecord:
    """GroupRecord definition."""

    group_id: str
    roles: set[str]
    members: set[str] = field(default_factory=set)


@dataclass(slots=True)
class ApiKeyRecord:
    """ApiKeyRecord definition."""

    key_id: str
    token: str
    label: str
    roles: set[str]
    capabilities: set[str]
    user_id: str | None = None
    revoked: bool = False


@dataclass(slots=True)
class ConfigEventRecord:
    """ConfigEventRecord definition."""

    event_id: str
    entity_type: str
    entity_id: str
    action: str
    actor: str
    payload: dict[str, Any]
    created_at: datetime


@dataclass(slots=True)
class CollectionRecord:
    """CollectionRecord definition."""

    profile: str
    collection: str
    description: str = ""
    dimensions: int | None = None
    distance_metric: str = "cosine"
    metadata: dict[str, Any] = field(default_factory=dict)
    allowed_roles: set[str] = field(default_factory=lambda: {"reader", "writer", "maintainer", "admin"})


@dataclass(slots=True)
class SourceConfigRecord:
    """SourceConfigRecord definition."""

    source_id: str
    source_type: str
    uri: str
    schedule: str
    profile: str
    collection: str
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class _CollectionManagerCompat:
    """Minimal compatibility shim for legacy unit paths that expect collection_manager."""

    def __init__(self, service: IndexService) -> None:
        self._service = service

    def create(self, collection_key: str) -> None:
        profile, collection = self._split_key(collection_key)
        self._service._ensure_collection_record(profile, collection)

    def list(self, profile: str) -> list[str]:
        return self._service.collections_list(profile)

    def delete(self, collection_key: str) -> None:
        self._service.collections.pop(collection_key, None)
        self._service.collection_roles.pop(collection_key, None)

    @staticmethod
    def _split_key(collection_key: str) -> tuple[str, str]:
        if ":" in collection_key:
            profile, collection = collection_key.split(":", 1)
            return profile, collection
        return "default", collection_key


class IndexService:
    """Service facade providing deterministic behaviour for all tool flows."""

    _instances: ClassVar[weakref.WeakSet[IndexService]] = weakref.WeakSet()

    def __init__(
        self,
        audit_path: str,
        *,
        embedding_provider: str | None = None,
        embedding_model: str | None = None,
        default_backend: str | None = None,
        queue_database_url: str | None = None,
        server_id: str | None = None,
    ) -> None:
        """Initialise the instance state."""
        resolved_provider = embedding_provider or _required_env(
            "CLOUD_DOG__INDEX__EMBEDDING__PROVIDER",
            "EMBED_PROVIDER",
        )
        resolved_model = embedding_model or _required_env(
            "CLOUD_DOG__INDEX__EMBEDDING__MODEL",
            "EMBED_MODEL",
        )
        resolved_backend = default_backend or _required_env(
            "CLOUD_DOG__INDEX__VDB__PROVIDER",
            "INDEX_RETRIEVER_DEFAULT_BACKEND",
        )

        self._default_backend = resolved_backend.strip().lower() or "chroma"
        self._runtime_tree = _load_runtime_tree()
        self._env_tier = _resolve_env_tier(self._runtime_tree)
        self._live_backend_mode = self._env_tier in {"ST", "IT", "AT", "CT"}
        self._loop = asyncio.new_event_loop()
        self._loop_thread: threading.Thread | None = None
        self._loop_ready = threading.Event()
        self._loop_executor: Any | None = None
        self._loop_future: Any | None = None
        self._llm_provider = resolved_provider.strip().lower() or "ollama"
        self._llm_model = resolved_model
        self._embedding_dimension_cache: int | None = None
        self._async_job_execution = self._live_backend_mode
        self._job_threads: dict[str, threading.Thread] = {}
        self._job_threads_lock = threading.Lock()
        self._closed = False
        # W28A-323: per-profile ingest concurrency cap. Serialises embedding
        # calls within the same profile to avoid Ollama contention that causes
        # 480s tail-latency timeouts. Cross-profile calls run in parallel.
        _max_per_profile = int(os.environ.get(
            "CLOUD_DOG__INDEX__INGEST__MAX_CONCURRENCY_PER_PROFILE", "1"
        ))
        self._ingest_semaphores: dict[str, threading.Semaphore] = {}
        self._ingest_semaphore_max = max(1, _max_per_profile)
        self._ingest_semaphore_lock = threading.Lock()
        self._ingest_last_latency: dict[str, float] = {}
        self._ingest_queue_depth: dict[str, int] = {}
        self._instances.add(self)
        self._ensure_loop_thread()
        self.vdb = self._build_vdb_client()
        self._llm_client = self._build_llm_client()
        resolved_queue_database_url = queue_database_url or _resolve_queue_database_url(audit_path)
        resolved_server_id = server_id or _resolve_server_id()
        # Queue config read via cloud_dog_config.get_config (PS-75 JQ1).
        def _q_cfg(key: str, default: Any) -> Any:
            try:
                from cloud_dog_config import get_config
                val = get_config(f"queue.{key}")
                return val if val is not None else default
            except Exception:
                return default

        self.queue = QueueEngine(
            database_url=resolved_queue_database_url,
            server_id=resolved_server_id,
            queue_name=str(_q_cfg("name", "index-retriever")),
            timeout_seconds=int(_q_cfg("default_timeout_seconds", 1800)),
            queue_wait_timeout_seconds=int(_q_cfg("queue_wait_timeout_seconds", 1800)),
            claim_timeout_seconds=int(_q_cfg("claim_timeout_seconds", 60)),
            retry_max_attempts=int(_q_cfg("retry.max_attempts", 3)),
            retry_backoff_seconds=float(_q_cfg("retry.backoff_seconds", 5.0)),
            redis_enabled=_env_bool("CLOUD_DOG__INDEX__QUEUE__REDIS__ENABLED", default=False),
            redis_url=_env_or_default("CLOUD_DOG__INDEX__QUEUE__REDIS__URL", ""),
        )
        self.audit_logger = AuditLogger(
            path=audit_path,
            server_id=self.queue.server_id,
            environment=_resolve_environment(),
        )
        self.queue.set_audit_logger(self.audit_logger)
        self.embedding_adapter = EmbeddingAdapter(provider=resolved_provider, model=resolved_model)
        self.profiles: dict[str, dict[str, Any]] = {
            "default": {
                "enabled": True,
                "backend": self._default_backend,
                "roles": {"reader", "writer", "maintainer", "admin"},
            }
        }
        # W28A-295: load additional profiles from config (defaults.yaml + env merge).
        # The runtime tree profiles section may define profiles beyond 'default' (e.g.
        # multilang with bge-m3). Env-var overrides for the top-level index.* settings
        # must NOT erase YAML-defined profiles.
        yaml_profiles = _nested_mapping(self._runtime_tree, "profiles")
        for pname, pcfg in yaml_profiles.items():
            if pname == "default" or not isinstance(pcfg, dict):
                continue
            if not pcfg.get("enabled", True):
                continue
            vdb_cfg = _nested_mapping(pcfg, "vdb")
            embed_cfg = _nested_mapping(pcfg, "embeddings")
            self.profiles[pname] = {
                "enabled": True,
                "backend": str(vdb_cfg.get("type", self._default_backend)).strip().lower(),
                "roles": {"reader", "writer", "maintainer", "admin"},
                "embeddings": embed_cfg,
                "vdb": vdb_cfg,
            }
        self.collections: dict[str, CollectionRecord] = {}
        self.collection_roles: dict[str, set[str]] = {}
        self.source_configs: dict[str, SourceConfigRecord] = {}
        self.documents: dict[str, DocumentRecord] = {}
        self.idempotency: dict[str, str] = {}
        self.stream_sessions: dict[str, StreamSession] = {}
        self._stored_files: dict[str, dict[str, Any]] = {}  # W28C-427 IDX-SNAG-002 PS-78 file store
        self._job_handlers: dict[str, Any] = {}
        self.collection_manager = _CollectionManagerCompat(self)
        self.users: dict[str, UserRecord] = {}
        self.groups: dict[str, GroupRecord] = {}
        self.api_keys: dict[str, ApiKeyRecord] = {}
        self._idam_users = UserService() if UserService is not None else None
        self._idam_groups = GroupService() if GroupService is not None else None
        self._idam_api_keys = APIKeyManager(default_prefix="cd_") if APIKeyManager is not None else None
        self._idam_api_key_refs: dict[str, str] = {}
        self.a2a_events: list[ConfigEventRecord] = []
        self._auth_api_keys: dict[str, set[str]] = {}
        self._auth_api_keys_bound = False
        self.queue.register_handler("ingest_text", self._process_ingest_text_job)
        # W28A-F-RF-07-L3: durable admin state via bootstrap-seed. Each of the
        # four service processes (api_server, web_server, mcp_server, a2a_server)
        # constructs its own IndexService with empty in-memory admin stores.
        # The seed re-applies the desired users / groups / collections / api-keys
        # on every startup so admin state survives container restarts. If a seed
        # file exists AND contains api-keys but Vault is unreachable, this
        # raises BootstrapSeedError — by design (no silent empty-state start).
        try:
            from index_tools.bootstrap import maybe_apply_bootstrap_seed
        except Exception:  # pragma: no cover — import-time failure of the loader
            maybe_apply_bootstrap_seed = None  # type: ignore[assignment]
        if maybe_apply_bootstrap_seed is not None:
            maybe_apply_bootstrap_seed(self)
        # W28A-323: warm-up embedder models at startup.
        self._warm_embedders()

    def _run_async(self, coro: Any) -> Any:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        self._ensure_loop_thread()
        if running_loop is self._loop:
            raise RuntimeError("IndexService cannot block on its own async loop thread")
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def _ensure_loop_thread(self) -> None:
        if getattr(self, "_loop_future", None) is not None and not self._loop_future.done() and self._loop.is_running():
            return

        def _runner() -> None:
            asyncio.set_event_loop(self._loop)
            self._loop_ready.set()
            self._loop.run_forever()

        self._loop_ready.clear()
        # Daemon thread for the async event loop. This is NOT a job queue
        # operation — it runs the asyncio loop that hosts MCP/tool handlers.
        # It cannot be routed through cloud_dog_jobs because it IS the loop
        # that cloud_dog_jobs handlers execute within.
        from concurrent.futures import ThreadPoolExecutor
        self._loop_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="index-service-async-loop")
        self._loop_future = self._loop_executor.submit(_runner)
        self._loop_thread = None
        self._loop_ready.wait(timeout=float(_cfg("queue.startup_wait_seconds", 1.0) or 1.0))

    def close(self) -> None:
        """Stop service-owned background workers."""
        if self._closed:
            return
        self._closed = True
        with self._job_threads_lock:
            job_threads = list(self._job_threads.values())
            self._job_threads.clear()
        for thread in job_threads:
            if thread.is_alive():
                thread.join(timeout=5)

        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        executor = self._loop_executor
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
            self._loop_executor = None
            self._loop_future = None
        if not self._loop.is_closed():
            self._loop.close()

    def _get_ingest_semaphore(self, profile: str) -> threading.Semaphore:
        """Return (lazily creating) the per-profile ingest semaphore."""
        with self._ingest_semaphore_lock:
            if profile not in self._ingest_semaphores:
                self._ingest_semaphores[profile] = threading.Semaphore(self._ingest_semaphore_max)
            return self._ingest_semaphores[profile]

    def _warm_embedders(self) -> None:
        """W28A-323: pre-load embedder models at startup to avoid cold-start latency.

        Runs in a daemon thread to avoid blocking service startup. Failures
        are logged as warnings — actual ingest calls will trigger lazy load.
        Skipped in test mode (UT/ST) where no live embedder is available.
        """
        if not self._live_backend_mode:
            return

        def _warmup() -> None:
            for pname in list(self.profiles.keys()):
                try:
                    dim = self._embedding_dimension()
                    logger.info("W28A-323 embedder warm-up completed", profile=pname, dimension=dim)
                except Exception as exc:
                    logger.warning("W28A-323 embedder warm-up failed", profile=pname, error=str(exc))

        t = threading.Thread(target=_warmup, daemon=True, name="embedder-warmup")
        t.start()

    def ingest_health(self) -> dict[str, Any]:
        """W28A-323: return per-profile ingest pipeline health."""
        profiles_status: dict[str, dict[str, Any]] = {}
        for pname in list(self.profiles.keys()):
            sem = self._get_ingest_semaphore(pname)
            # Semaphore._value is the internal counter (available permits)
            available = getattr(sem, "_value", self._ingest_semaphore_max)
            queue_depth = self._ingest_queue_depth.get(pname, 0)
            last_latency = self._ingest_last_latency.get(pname)
            # Probe embedder warm status
            embedder_warm = False
            try:
                if self._llm_client is not None:
                    embedder_warm = True
                elif self.embedding_adapter is not None:
                    embedder_warm = True
            except Exception:
                pass
            profiles_status[pname] = {
                "queue_depth": queue_depth,
                "available_slots": available,
                "max_concurrency": self._ingest_semaphore_max,
                "embedder_warm": embedder_warm,
                "last_latency_ms": round(last_latency * 1000, 1) if last_latency is not None else None,
            }
        return {"ok": True, "profiles": profiles_status}

    @classmethod
    def close_all_instances(cls) -> None:
        """Close any service instances still alive in the process."""
        for instance in list(cls._instances):
            instance.close()

    def _profile_provider(self, profile: str) -> str:
        payload = self.profiles.get(profile, self.profiles.get("default", {}))
        provider = str(payload.get("backend", self._default_backend)).strip().lower()
        return provider or self._default_backend

    def _build_vdb_client(self) -> Any:
        if get_vdb_client is None:
            raise RuntimeError("cloud_dog_vdb is required")

        # A123: profile_vdb / profile_chroma were used by the old silent
        # local_mode fallback. The new contract derives chroma_local_mode
        # purely from tier + explicit env flag, so the profile_default
        # snippet is no longer needed here.
        index_vdb = _nested_mapping(self._runtime_tree, "index", "vdb")

        chroma_url = str(index_vdb.get("chroma_url", "")).strip()
        qdrant_url = str(index_vdb.get("qdrant_url", "")).strip()
        default_backend = self._default_backend
        required_providers = {
            provider.strip().lower()
            for provider in str(_cfg("index.live_required_providers", "")
                                or _cfg("INDEX_RETRIEVER_LIVE_REQUIRED_PROVIDERS", "")
                                or "").split(",")
            if provider.strip()
        }
        vector_stores: dict[str, Any] = {"default_backend": default_backend}

        # A123/A117 root-cause fix: the previous fallback dropped chroma into
        # in-memory local_mode whenever the *defaults.yaml* profile happened to
        # carry `vdb.chroma.mode: local` and the operator hadn't supplied
        # CHROMA_URL — even in a live preprod tier. That made every chroma
        # profile silently store data in transient process memory using the
        # `deterministic_vector` hash fallback, and it disappeared on every
        # container restart. The new contract is explicit:
        #   - non-live tier (default for unit tests): always local_mode
        #   - live tier (ST/IT/AT/CT): local_mode requires an explicit opt-in
        #     via CLOUD_DOG__INDEX__VDB__CHROMA_LOCAL_MODE=true. If chroma_url
        #     is empty and the explicit flag is unset, the chroma backend is
        #     simply not registered, so creating a profile with
        #     `backend: chroma` fails loudly. RULES §1.4 — fail loud, never
        #     silently substitute.
        chroma_local_mode_flag = str(
            _env_or_default("CLOUD_DOG__INDEX__VDB__CHROMA_LOCAL_MODE", "")
        ).strip().lower() in {"1", "true", "yes", "on"}
        # W28A-296: if a remote Chroma URL is configured, never use local mode.
        if chroma_url:
            chroma_local_mode = False
        elif self._live_backend_mode:
            chroma_local_mode = chroma_local_mode_flag
        else:
            chroma_local_mode = True
        if chroma_url or chroma_local_mode:
            vector_stores["chroma"] = {
                "enabled": True,
                "base_url": chroma_url,
                "timeout_seconds": 120,
                "local_mode": chroma_local_mode,
            }

        # W28A-296: if a remote Qdrant URL is configured, NEVER use local mode
        # regardless of env tier. Local mode stores data in process memory which
        # is lost on every container restart — a silent data-loss defect on preprod.
        qdrant_local_mode = not qdrant_url and "qdrant" in required_providers
        if qdrant_url or qdrant_local_mode:
            vector_stores["qdrant"] = {
                "enabled": True,
                "base_url": qdrant_url,
                "api_key": str(index_vdb.get("qdrant_api_key", "")).strip(),
                "timeout_seconds": 120,
                "local_mode": not bool(qdrant_url),
            }

        pgvector_database_uri = _env_or_default("CLOUD_DOG__INDEX__VDB__PGVECTOR_DATABASE_URI", "")
        if pgvector_database_uri:
            vector_stores["pgvector"] = {
                "enabled": True,
                "database_uri": pgvector_database_uri,
                "timeout_seconds": 120,
                "local_mode": False,
            }

        weaviate_url = _env_or_default("CLOUD_DOG__INDEX__VDB__WEAVIATE_URL", "")
        if not weaviate_url:
            weaviate_host = _env_or_default("CLOUD_DOG__INDEX__VDB__WEAVIATE_HOST", "")
            weaviate_port = _env_or_default("CLOUD_DOG__INDEX__VDB__WEAVIATE_PORT", "8080")
            weaviate_scheme = "http"
            weaviate_url = f"{weaviate_scheme}://{weaviate_host}:{weaviate_port}" if weaviate_host else ""
        if weaviate_url:
            vector_stores["weaviate"] = {
                "enabled": True,
                "base_url": weaviate_url,
                "api_key": _env_or_default("CLOUD_DOG__INDEX__VDB__WEAVIATE_API_KEY", ""),
                "timeout_seconds": 120,
                "local_mode": False,
            }

        infinity_url = _env_or_default("CLOUD_DOG__INDEX__VDB__INFINITY_URL", "")
        if not infinity_url:
            infinity_host = _env_or_default("CLOUD_DOG__INDEX__VDB__INFINITY_HOST", "")
            infinity_port = _env_or_default("CLOUD_DOG__INDEX__VDB__INFINITY_PORT", "23817")
            infinity_scheme = "http"
            infinity_url = f"{infinity_scheme}://{infinity_host}:{infinity_port}" if infinity_host else ""
        if infinity_url:
            vector_stores["infinity"] = {
                "enabled": True,
                "base_url": infinity_url,
                "api_key": _env_or_default("CLOUD_DOG__INDEX__VDB__INFINITY_API_KEY", ""),
                "database": _env_or_default("CLOUD_DOG__INDEX__VDB__INFINITY_DATABASE", "default_db"),
                "timeout_seconds": 120,
                "local_mode": False,
            }

        opensearch_url = _env_or_default("CLOUD_DOG__INDEX__VDB__OPENSEARCH_URL", "")
        if not opensearch_url:
            opensearch_host = _env_or_default("CLOUD_DOG__INDEX__VDB__OPENSEARCH_HOST", "")
            opensearch_port = _env_or_default("CLOUD_DOG__INDEX__VDB__OPENSEARCH_PORT", "9200")
            opensearch_scheme = "https" if str(opensearch_port).strip() == "443" else "http"
            opensearch_url = f"{opensearch_scheme}://{opensearch_host}:{opensearch_port}" if opensearch_host else ""
        if opensearch_url:
            vector_stores["opensearch"] = {
                "enabled": True,
                "base_url": opensearch_url,
                "username": _env_or_default("CLOUD_DOG__INDEX__VDB__OPENSEARCH_USERNAME", ""),
                "password": _env_or_default("CLOUD_DOG__INDEX__VDB__OPENSEARCH_PASSWORD", ""),
                "timeout_seconds": 120,
                "local_mode": False,
            }

        return get_vdb_client(
            {
                "vector_stores": vector_stores,
                "embeddings": self._resolved_embedding_settings(),
            }
        )

    def _resolved_embedding_settings(self) -> dict[str, Any]:
        profile_default = _nested_mapping(self._runtime_tree, "profiles", "default")
        embeddings = _nested_mapping(profile_default, "embeddings")
        openai_compat = _nested_mapping(embeddings, "openai_compat")
        base_url = str(openai_compat.get("base_url", "")).strip() or _env_or_default("EMBED_BASE_URL", "")
        api_key = str(openai_compat.get("api_key", "")).strip() or _env_or_default("EMBED_API_KEY", "")
        timeout_seconds = int(openai_compat.get("timeout_seconds", 60) or 60)
        return {
            "provider": self._llm_provider,
            self._llm_provider: {
                "base_url": base_url,
                "api_key": api_key,
                "model": self._llm_model,
                "timeout_seconds": timeout_seconds,
            },
        }

    def _build_llm_client(self) -> Any | None:
        if get_llm_client is None:
            return None
        resolved = self._resolved_embedding_settings()
        provider_cfg = _nested_mapping(resolved, self._llm_provider)
        base_url = str(provider_cfg.get("base_url", "")).strip()
        api_key = str(provider_cfg.get("api_key", "")).strip()
        if not base_url:
            return None
        return get_llm_client(
            {
                "llm": {"default_provider": self._llm_provider},
                "providers": {
                    self._llm_provider: {
                        "enabled": True,
                        "base_url": base_url,
                        "model": self._llm_model,
                        "api_key": api_key,
                        "timeout_seconds": int(provider_cfg.get("timeout_seconds", 300) or 300),
                    }
                },
            }
        )

    def _embedding_dimension(self) -> int:
        if self._embedding_dimension_cache is not None:
            return self._embedding_dimension_cache
        if self._llm_client is not None:
            try:
                vectors = self._run_async(
                    asyncio.wait_for(
                        self._llm_client.embed(
                            ["dimension probe"],
                            provider_id=self._llm_provider,
                            model=self._llm_model,
                        ),
                        timeout=float(_cfg_val("queue.llm_probe_timeout_seconds", 30.0)),
                    )
                )
                if vectors:
                    self._embedding_dimension_cache = len(vectors[0])
            except Exception:
                self._embedding_dimension_cache = None
        if self._embedding_dimension_cache is None:
            self._embedding_dimension_cache = 1024
        return self._embedding_dimension_cache

    def _ensure_backend_collection(self, profile: str, collection: str) -> str:
        if CollectionSpec is None:
            raise RuntimeError("cloud_dog_vdb CollectionSpec is required")
        provider_id = self._profile_provider(profile)
        backend_name = self._backend_collection_name(profile, collection, provider_id=provider_id)
        record = self.collections.get(self._collection_key(profile, collection))
        existing = self._run_async(self.vdb.get_collection(backend_name, provider_id=provider_id))
        if (
            existing is not None
            and os.environ.get("INDEX_RETRIEVER_TEST_RUN_PREFIX", "").strip()
            and provider_id == "weaviate"
            and record is not None
            and not record.metadata.get("backend_collection_ready")
        ):
            self._run_async(self.vdb.delete_collection(backend_name, provider_id=provider_id))
            existing = None
        if existing is None:
            self._run_async(
                self.vdb.create_collection(
                    CollectionSpec(
                        name=backend_name,
                        embedding_dim=self._embedding_dimension(),
                        metadata={"embedding_model": self._llm_model},
                    ),
                    provider_id=provider_id,
                )
            )
        if record is not None:
            record.metadata.pop("backend_binding_pending", None)
            record.metadata["backend_collection_ready"] = True
        return backend_name

    @staticmethod
    def _collection_key(profile: str, collection: str) -> str:
        """Internal helper to collection key."""
        return f"{profile}:{collection}"

    @staticmethod
    def _backend_collection_name(profile: str, collection: str, provider_id: str | None = None) -> str:
        """Return a backend-safe physical collection name for the VDB layer."""
        provider = str(provider_id or "").strip().lower()
        run_prefix = os.environ.get("INDEX_RETRIEVER_TEST_RUN_PREFIX", "").strip().lower()
        namespace = f"indexretriever_{run_prefix}" if run_prefix else "indexretriever"
        base_name = _safe_backend_name(f"{namespace}_{profile}_{collection}")
        if provider == "pgvector" and base_name[:1].isdigit():
            base_name = f"idx_{base_name}"
        if provider != "infinity":
            return base_name
        digest = sha256(base_name.encode("utf-8")).hexdigest()[:18]
        return f"idxinf_{digest}"

    def _require_admin(self, roles: set[str]) -> None:
        """Internal helper to require admin."""
        if "admin" not in roles:
            raise PermissionError("Admin role required")

    @staticmethod
    def _collection_payload(record: CollectionRecord) -> dict[str, Any]:
        """Serialise collection state for API and MCP responses."""
        return {
            "profile": record.profile,
            "collection": record.collection,
            "description": record.description,
            "dimensions": record.dimensions,
            "distance_metric": record.distance_metric,
            "metadata": dict(record.metadata),
            "allowed_roles": sorted(record.allowed_roles),
        }

    @staticmethod
    def _source_config_payload(record: SourceConfigRecord) -> dict[str, Any]:
        """Serialise source-config state for API and MCP responses."""
        return {
            "source_id": record.source_id,
            "source_type": record.source_type,
            "uri": record.uri,
            "schedule": record.schedule,
            "profile": record.profile,
            "collection": record.collection,
            "enabled": record.enabled,
            "metadata": dict(record.metadata),
        }

    def _ensure_collection_record(self, profile: str, collection: str) -> CollectionRecord:
        """Create or return the runtime collection record."""
        collection_key = self._collection_key(profile, collection)
        record = self.collections.get(collection_key)
        if record is not None:
            return record
        allowed_roles = set(self.collection_roles.get(collection_key, {"reader", "writer", "maintainer", "admin"}))
        record = CollectionRecord(
            profile=profile,
            collection=collection,
            allowed_roles=allowed_roles,
        )
        self.collections[collection_key] = record
        self.collection_roles[collection_key] = set(record.allowed_roles)
        return record

    def attach_auth_api_keys(self, auth_api_keys: dict[str, set[str]]) -> None:
        """Bind the runtime auth API-key store so admin key CRUD updates auth immediately."""
        self._auth_api_keys = auth_api_keys
        self._auth_api_keys_bound = True
        for key_id in sorted(self.api_keys.keys()):
            self._sync_auth_api_key_record(self.api_keys[key_id])

    def _effective_user_roles(self, user_id: str) -> set[str]:
        record = self.users.get(user_id)
        if record is None:
            return set()
        roles = set(record.roles)
        for group_id in record.groups:
            group = self.groups.get(group_id)
            if group is not None:
                roles.update(group.roles)
        return roles

    def _sync_auth_api_key_record(self, record: ApiKeyRecord) -> None:
        if not self._auth_api_keys_bound:
            return
        if record.revoked:
            self._auth_api_keys.pop(record.token, None)
            return
        effective_roles = set(record.roles)
        if record.user_id:
            effective_roles.update(self._effective_user_roles(record.user_id))
        self._auth_api_keys[record.token] = effective_roles

    def _refresh_auth_api_keys_for_user(self, user_id: str) -> None:
        for record in self.api_keys.values():
            if record.user_id == user_id:
                self._sync_auth_api_key_record(record)

    def _refresh_auth_api_keys_for_group(self, group_id: str) -> None:
        impacted_users = sorted(
            user_id
            for user_id, record in self.users.items()
            if group_id in record.groups
        )
        for user_id in impacted_users:
            self._refresh_auth_api_keys_for_user(user_id)

    def _sync_idam_user(self, user_id: str) -> None:
        if self._idam_users is None or IDAMUser is None or IDAMUserStatus is None:
            return
        record = self.users[user_id]
        existing = self._idam_users.get(user_id)
        primary_role = sorted(record.roles)[0] if record.roles else "reader"
        status = IDAMUserStatus.ACTIVE if record.enabled else IDAMUserStatus.DISABLED
        if existing is None:
            self._idam_users.create(
                IDAMUser(
                    user_id=user_id,
                    username=user_id,
                    display_name=record.display_name,
                    role=primary_role,
                    status=status,
                    email="",
                )
            )
            return
        self._idam_users.update(
            user_id,
            username=user_id,
            display_name=record.display_name,
            role=primary_role,
            status=status,
        )

    def _sync_idam_group(self, group_id: str) -> None:
        if self._idam_groups is None or IDAMGroup is None:
            return
        record = self.groups[group_id]
        known_ids = {item.group_id for item in self._idam_groups.list()}
        if group_id not in known_ids:
            self._idam_groups.create(
                IDAMGroup(
                    group_id=group_id,
                    name=group_id,
                    description=",".join(sorted(record.roles)),
                )
            )
        for member in sorted(record.members):
            self._idam_groups.add_member(group_id, member)

    def _profile_payload(self, profile: str) -> dict[str, Any]:
        payload = dict(self.profiles[profile])
        roles = payload.get("roles")
        if isinstance(roles, set):
            payload["roles"] = sorted(roles)
        return payload

    @staticmethod
    def _serialise_profile_payload(payload: dict[str, Any]) -> dict[str, Any]:
        output = dict(payload)
        roles = output.get("roles")
        if isinstance(roles, set):
            output["roles"] = sorted(roles)
        return output

    def _emit_config_event(
        self,
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str,
        payload: dict[str, Any],
    ) -> None:
        self.a2a_events.append(
            ConfigEventRecord(
                event_id=str(uuid4()),
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                actor=actor,
                payload=payload,
                created_at=datetime.now(timezone.utc),
            )
        )

    def _process_ingest_text_job(self, job: JobRecord) -> None:
        """Execute the ingest pipeline for a queued job record.

        W28A-323: acquires a per-profile semaphore to serialise embedding calls
        within the same profile, preventing Ollama contention that causes 480s
        tail-latency timeouts.
        """
        payload = dict(job.payload)
        profile = str(payload["profile"])
        sem = self._get_ingest_semaphore(profile)
        self._ingest_queue_depth[profile] = self._ingest_queue_depth.get(profile, 0) + 1
        t0 = time.monotonic()
        try:
            sem.acquire()
            try:
                self._process_ingest_text_job_inner(job)
            finally:
                sem.release()
        finally:
            elapsed = time.monotonic() - t0
            self._ingest_last_latency[profile] = elapsed
            depth = self._ingest_queue_depth.get(profile, 1)
            self._ingest_queue_depth[profile] = max(0, depth - 1)

    def _process_ingest_text_job_inner(self, job: JobRecord) -> None:
        """Execute the ingest pipeline (called under per-profile semaphore)."""
        payload = dict(job.payload)
        profile = str(payload["profile"])
        collection = str(payload["collection"])
        text = str(payload["text"])
        source = str(payload["source"])
        actor = str(payload.get("actor", "system"))
        metadata = payload.get("metadata")
        created_at_raw = str(payload.get("created_at", "")).strip()
        created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else None

        if Record is None:
            raise RuntimeError("cloud_dog_vdb Record is required")
        self._ensure_backend_collection(profile, collection)
        self._raise_if_job_cancelled(job.job_id)
        self.queue.record_progress(
            job.job_id,
            phase="preparing",
            percentage=30,
            message="validating ingest payload",
            extra={"source": source},
        )
        provider_id = self._profile_provider(profile)
        backend_collection = self._backend_collection_name(profile, collection, provider_id=provider_id)
        chunks = token_chunks(text, chunk_size=64, chunk_overlap=8)
        if not chunks:
            chunks = [text]
        self._raise_if_job_cancelled(job.job_id)
        self.queue.record_progress(
            job.job_id,
            phase="chunked",
            percentage=50,
            message="content chunked for ingestion",
            extra={"chunk_count": len(chunks)},
        )
        document_metadata = build_metadata(
            source=source,
            content=text.encode(),
            profile=profile,
            collection=collection,
            caller_metadata=metadata if isinstance(metadata, dict) else None,
        )
        document_metadata = _merge_document_metadata(
            document_metadata,
            metadata if isinstance(metadata, dict) else None,
        )
        source_uri = str(document_metadata.get("source_uri", source))
        for existing in self.documents.values():
            if (
                existing.profile == profile
                and existing.collection == collection
                and str(existing.metadata.get("source_uri", existing.source)) == source_uri
                and str(existing.metadata.get("lifecycle_state", "active")) == "active"
            ):
                document_metadata = merge_provenance(document_metadata, existing.metadata)
                break
        self._raise_if_job_cancelled(job.job_id)
        created_value = (created_at or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")  # noqa: UP017
        document_metadata["created_at"] = created_value
        document_metadata["source"] = str(document_metadata.get("source_uri", source))
        document_metadata.setdefault("actor", actor)
        document_metadata.setdefault("profile", profile)
        document_metadata.setdefault("collection", collection)
        document_metadata["tenant_id"] = profile
        document_metadata["namespace"] = f"{profile}:{collection}"
        document_metadata["lifecycle_state"] = "active"
        document_metadata["is_latest"] = True
        document_metadata["embedding_model"] = self._llm_model
        document_metadata["embedding_dim"] = self._embedding_dimension()
        document_metadata["chunker"] = "token_chunks"
        document_metadata["chunker_version"] = "v1"
        document_metadata["token_count"] = len(text.split())
        document_metadata["user_id"] = str(document_metadata.get("user_id") or actor)
        document_metadata["parser_name"] = str(document_metadata.get("parser_name") or "internal")
        document_metadata["parser_provider"] = str(document_metadata.get("parser_provider") or "internal")
        document_metadata.setdefault("indexing_signature", self._llm_model)
        document_metadata = _apply_metadata_pack_aliases(document_metadata)
        metadata_errors = validate_metadata(document_metadata)
        if metadata_errors:
            raise ValueError(f"Invalid document metadata: {'; '.join(metadata_errors)}")
        doc_id = str(document_metadata["doc_id"])
        record_id = str(document_metadata["record_id"])
        superseded_record_ids: list[str] = []
        superseded_records: list[Any] = []
        superseded_snapshots: list[tuple[DocumentRecord, dict[str, Any]]] = []
        for existing in self.documents.values():
            if (
                existing.profile == profile
                and existing.collection == collection
                and str(existing.metadata.get("source_uri", existing.source)) == source_uri
                and str(existing.record_id or existing.doc_id) != record_id
                and str(existing.metadata.get("lifecycle_state", "active")) == "active"
            ):
                superseded_snapshots.append((existing, dict(existing.metadata)))
                existing.metadata.update(mark_superseded(existing.metadata, new_record_id=record_id))
                _apply_metadata_pack_aliases(existing.metadata)
                superseded_record_ids.append(str(existing.record_id or existing.doc_id))
                superseded_records.append(
                    Record(
                        record_id=str(existing.record_id or existing.doc_id),
                        content=existing.text,
                        metadata=dict(existing.metadata),
                    )
                )
        self.queue.record_progress(
            job.job_id,
            phase="embedding_upsert",
            percentage=75,
            message="upserting document into vector store",
            extra={"doc_id": doc_id, "record_id": record_id},
        )
        self._raise_if_job_cancelled(job.job_id)
        created = created_at or datetime.now(timezone.utc)  # noqa: UP017
        document_record = DocumentRecord(
            doc_id=doc_id,
            record_id=record_id,
            profile=profile,
            collection=collection,
            source=source_uri,
            text=text,
            metadata=document_metadata,
            created_at=created,
        )
        self.documents[record_id] = document_record
        records_to_upsert = [Record(record_id=record_id, content=text, metadata=document_metadata)]
        if provider_id != "weaviate":
            records_to_upsert = superseded_records + records_to_upsert
        try:
            self._run_async(
                self.vdb.upsert_records(
                    backend_collection,
                    records_to_upsert,
                    provider_id=provider_id,
                )
            )
            self._raise_if_job_cancelled(job.job_id)
        except Exception:
            self.documents.pop(record_id, None)
            for existing, previous_metadata in superseded_snapshots:
                existing.metadata = previous_metadata
            raise
        self.queue.record_progress(
            job.job_id,
            phase="persisted",
            percentage=90,
            message="document persisted and indexed",
            extra={"doc_id": doc_id, "record_id": record_id, "collection": collection},
        )
        audit_metadata = dict(document_metadata)
        audit_metadata["dedupe_decision"] = "version" if superseded_record_ids else "ingest"
        if superseded_record_ids:
            audit_metadata["superseded_record_ids"] = superseded_record_ids
        self.audit_logger.log_ingest(
            actor=actor,
            profile=profile,
            collection=collection,
            job_id=job.job_id,
            source=source,
            metadata=audit_metadata,
            chunk_count=len(chunks),
        )

    def _raise_if_job_cancelled(self, job_id: str) -> None:
        """Abort cooperative job execution when the queue state is cancelled."""
        if self.queue.get(job_id).status is JobStatus.cancelled:
            raise JobCancelledError(f"Job {job_id} was cancelled")

    def _dispatch_job_async(self, job_id: str) -> None:
        """Run a queued job in a detached worker thread when live execution is enabled."""
        if not self._async_job_execution:
            try:
                self.queue.run(job_id=job_id)
            except Exception:
                pass
            return
        job = self.queue.get(job_id)
        if (
            os.environ.get("INDEX_RETRIEVER_TEST_RUN_PREFIX", "").strip()
            and self._profile_provider(job.profile) in {"infinity", "weaviate"}
        ):
            try:
                self.queue.run(job_id=job_id)
            except Exception:
                pass
            return

        with self._job_threads_lock:
            existing = self._job_threads.get(job_id)
            if existing is not None and existing.is_alive():
                return

            def _runner() -> None:
                try:
                    self.queue.run(job_id=job_id)
                except Exception:
                    pass
                finally:
                    with self._job_threads_lock:
                        current = self._job_threads.get(job_id)
                        if current is threading.current_thread():
                            self._job_threads.pop(job_id, None)

            worker = threading.Thread(
                target=_runner,
                name=f"index-retriever-job-{job_id[:8]}",
                daemon=True,
            )
            self._job_threads[job_id] = worker
            worker.start()

    def profiles_list(self) -> list[str]:
        """Execute profiles list."""
        return sorted(self.profiles.keys())

    def profile_get(self, profile: str) -> dict[str, Any]:
        """Execute profile get."""
        return self._profile_payload(profile)

    def admin_profile_create(
        self,
        profile: str,
        roles: set[str],
        config: dict[str, Any] | None = None,
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Execute admin profile create."""
        # Covers: FR-03, CFG-01
        self._require_admin(roles)
        if profile in self.profiles:
            raise ValueError(f"Profile already exists: {profile}")
        payload = {
            "enabled": True,
            "backend": self.profiles["default"]["backend"],
            "roles": {"reader", "writer", "maintainer"},
        }
        if config:
            payload.update(dict(config))
        if "roles" in payload and isinstance(payload["roles"], list):
            payload["roles"] = set(str(item) for item in payload["roles"])
        elif "roles" not in payload:
            payload["roles"] = {"reader", "writer", "maintainer"}
        self.profiles[profile] = payload
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="create",
            target_type="profile",
            target_id=profile,
            target_name=profile,
            new_value=self._profile_payload(profile),
            profile=profile,
        )
        self._emit_config_event(
            entity_type="profile",
            entity_id=profile,
            action="created",
            actor=actor,
            payload=self._profile_payload(profile),
        )
        return self._profile_payload(profile)

    def admin_profile_update(
        self,
        profile: str,
        roles: set[str],
        updates: dict[str, Any],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Execute admin profile update."""
        # Covers: CFG-03
        self._require_admin(roles)
        if profile not in self.profiles:
            raise KeyError(profile)
        current = dict(self.profiles[profile])
        prior_payload = self._profile_payload(profile)
        current.update(dict(updates))
        if "roles" in current and isinstance(current["roles"], list):
            current["roles"] = set(str(item) for item in current["roles"])
        self.profiles[profile] = current
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="update",
            target_type="profile",
            target_id=profile,
            target_name=profile,
            prior_value=prior_payload,
            new_value=self._profile_payload(profile),
            profile=profile,
        )
        self._emit_config_event(
            entity_type="profile",
            entity_id=profile,
            action="updated",
            actor=actor,
            payload=self._profile_payload(profile),
        )
        return self._profile_payload(profile)

    def admin_profile_delete(self, profile: str, roles: set[str], actor: str = "admin") -> None:
        """Execute admin profile delete."""
        self._require_admin(roles)
        if profile == "default":
            raise ValueError("Default profile cannot be deleted")
        removed = self.profiles.pop(profile, None)
        if removed is None:
            raise KeyError(profile)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="delete",
            target_type="profile",
            target_id=profile,
            target_name=profile,
            prior_value=self._serialise_profile_payload(removed),
            profile=profile,
        )
        self._emit_config_event(
            entity_type="profile",
            entity_id=profile,
            action="deleted",
            actor=actor,
            payload={"profile": profile},
        )

    def users_list(self) -> list[dict[str, Any]]:
        """Return all configured users."""
        return [self.user_get(user_id) for user_id in sorted(self.users.keys())]

    def user_get(self, user_id: str) -> dict[str, Any]:
        """Return a configured user."""
        record = self.users[user_id]
        return {
            "user_id": record.user_id,
            "display_name": record.display_name,
            "roles": sorted(record.roles),
            "groups": sorted(record.groups),
            "enabled": record.enabled,
        }

    def admin_user_create(
        self,
        user_id: str,
        roles: set[str],
        payload: dict[str, Any],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Create a user record."""
        # Covers: CFG-08
        self._require_admin(roles)
        if user_id in self.users:
            raise ValueError(f"User already exists: {user_id}")
        record = UserRecord(
            user_id=user_id,
            display_name=str(payload.get("display_name", user_id)),
            roles=set(str(item) for item in payload.get("roles", ["reader"])),
            groups=set(str(item) for item in payload.get("groups", [])),
            enabled=bool(payload.get("enabled", True)),
        )
        self.users[user_id] = record
        self._sync_idam_user(user_id)
        self._refresh_auth_api_keys_for_user(user_id)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="create",
            target_type="user",
            target_id=user_id,
            target_name=user_id,
            new_value=self.user_get(user_id),
        )
        self._emit_config_event(
            entity_type="user",
            entity_id=user_id,
            action="created",
            actor=actor,
            payload=self.user_get(user_id),
        )
        return self.user_get(user_id)

    def admin_user_update(
        self,
        user_id: str,
        roles: set[str],
        payload: dict[str, Any],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Update a user record."""
        self._require_admin(roles)
        if user_id not in self.users:
            raise KeyError(user_id)
        record = self.users[user_id]
        prior_value = self.user_get(user_id)
        if "display_name" in payload:
            record.display_name = str(payload["display_name"])
        if "roles" in payload:
            record.roles = set(str(item) for item in payload["roles"])
        if "groups" in payload:
            record.groups = set(str(item) for item in payload["groups"])
        if "enabled" in payload:
            record.enabled = bool(payload["enabled"])
        self._sync_idam_user(user_id)
        self._refresh_auth_api_keys_for_user(user_id)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="update",
            target_type="user",
            target_id=user_id,
            target_name=user_id,
            prior_value=prior_value,
            new_value=self.user_get(user_id),
        )
        self._emit_config_event(
            entity_type="user",
            entity_id=user_id,
            action="updated",
            actor=actor,
            payload=self.user_get(user_id),
        )
        return self.user_get(user_id)

    def admin_user_delete(self, user_id: str, roles: set[str], actor: str = "admin") -> None:
        """Delete a user record."""
        self._require_admin(roles)
        prior_value = self.user_get(user_id)
        if self.users.pop(user_id, None) is None:
            raise KeyError(user_id)
        if self._idam_users is not None:
            self._idam_users.disable(user_id)
        self._refresh_auth_api_keys_for_user(user_id)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="delete",
            target_type="user",
            target_id=user_id,
            target_name=user_id,
            prior_value=prior_value,
        )
        self._emit_config_event(
            entity_type="user",
            entity_id=user_id,
            action="deleted",
            actor=actor,
            payload={"user_id": user_id},
        )

    def groups_list(self) -> list[dict[str, Any]]:
        """Return all configured groups."""
        return [self.group_get(group_id) for group_id in sorted(self.groups.keys())]

    def group_get(self, group_id: str) -> dict[str, Any]:
        """Return a configured group."""
        record = self.groups[group_id]
        return {
            "group_id": record.group_id,
            "roles": sorted(record.roles),
            "members": sorted(record.members),
        }

    def admin_group_create(
        self,
        group_id: str,
        roles: set[str],
        payload: dict[str, Any],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Create a group record."""
        # Covers: CFG-09
        self._require_admin(roles)
        if group_id in self.groups:
            raise ValueError(f"Group already exists: {group_id}")
        record = GroupRecord(
            group_id=group_id,
            roles=set(str(item) for item in payload.get("roles", [])),
            members=set(str(item) for item in payload.get("members", [])),
        )
        self.groups[group_id] = record
        self._sync_idam_group(group_id)
        self._refresh_auth_api_keys_for_group(group_id)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="create",
            target_type="group",
            target_id=group_id,
            target_name=group_id,
            new_value=self.group_get(group_id),
        )
        self._emit_config_event(
            entity_type="group",
            entity_id=group_id,
            action="created",
            actor=actor,
            payload=self.group_get(group_id),
        )
        return self.group_get(group_id)

    def admin_group_update(
        self,
        group_id: str,
        roles: set[str],
        payload: dict[str, Any],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Update a group record."""
        self._require_admin(roles)
        if group_id not in self.groups:
            raise KeyError(group_id)
        record = self.groups[group_id]
        prior_value = self.group_get(group_id)
        prior_members = set(record.members)
        if "roles" in payload:
            record.roles = set(str(item) for item in payload["roles"])
        if "members" in payload:
            record.members = set(str(item) for item in payload["members"])
        self._sync_idam_group(group_id)
        for member in sorted(prior_members.union(record.members)):
            self._refresh_auth_api_keys_for_user(member)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="update",
            target_type="group",
            target_id=group_id,
            target_name=group_id,
            prior_value=prior_value,
            new_value=self.group_get(group_id),
        )
        self._emit_config_event(
            entity_type="group",
            entity_id=group_id,
            action="updated",
            actor=actor,
            payload=self.group_get(group_id),
        )
        return self.group_get(group_id)

    def admin_group_delete(self, group_id: str, roles: set[str], actor: str = "admin") -> None:
        """Delete a group record."""
        self._require_admin(roles)
        prior_value = self.group_get(group_id)
        prior_members = set(self.groups[group_id].members)
        if self.groups.pop(group_id, None) is None:
            raise KeyError(group_id)
        for member in sorted(prior_members):
            self._refresh_auth_api_keys_for_user(member)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="delete",
            target_type="group",
            target_id=group_id,
            target_name=group_id,
            prior_value=prior_value,
        )
        self._emit_config_event(
            entity_type="group",
            entity_id=group_id,
            action="deleted",
            actor=actor,
            payload={"group_id": group_id},
        )

    def api_keys_list(self) -> list[dict[str, Any]]:
        """Return configured API keys without exposing full secrets."""
        records: list[dict[str, Any]] = []
        for key_id in sorted(self.api_keys.keys()):
            record = self.api_keys[key_id]
            records.append(
                {
                    "key_id": record.key_id,
                    "label": record.label,
                    "roles": sorted(record.roles),
                    "capabilities": sorted(record.capabilities),
                    "user_id": record.user_id,
                    "revoked": record.revoked,
                }
            )
        return records

    def admin_api_key_create(
        self,
        roles: set[str],
        payload: dict[str, Any],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Create an API key record and bind it into the active auth store."""
        # Covers: CFG-10
        self._require_admin(roles)
        key_id = str(payload.get("key_id", uuid4().hex[:12]))
        if key_id in self.api_keys:
            raise ValueError(f"API key already exists: {key_id}")
        token = str(payload.get("token", ""))
        idam_key_id = ""
        if self._idam_api_keys is not None:
            owner_id = str(payload.get("user_id") or actor or "api-key-owner")
            generated_token, metadata = self._idam_api_keys.generate(owner_id)
            token = token or generated_token
            idam_key_id = metadata.api_key_id
        if not token:
            token = f"cd_{uuid4().hex}"
        # Inherit owner user's role if no explicit roles provided
        # Accept both "user_id" and "owner_user_id" for the owner reference
        _owner_uid = payload.get("user_id") or payload.get("owner_user_id") or ""
        explicit_roles = payload.get("roles")
        if not explicit_roles and _owner_uid:
            owner_user = self.users.get(str(_owner_uid))
            if owner_user is not None:
                explicit_roles = list(getattr(owner_user, "roles", set()) or set())
            elif self._idam_users is not None:
                idam_user = self._idam_users.get(str(_owner_uid))
                if idam_user is not None:
                    idam_role = getattr(idam_user, "role", "")
                    if idam_role:
                        explicit_roles = [str(idam_role)]
        key_roles = set(str(item) for item in (explicit_roles or ["reader"]))
        record = ApiKeyRecord(
            key_id=key_id,
            token=token,
            label=str(payload.get("label", key_id)),
            roles=key_roles,
            capabilities=set(str(item) for item in payload.get("capabilities", [])),
            user_id=str(_owner_uid) if _owner_uid else None,
        )
        self.api_keys[key_id] = record
        if idam_key_id:
            self._idam_api_key_refs[key_id] = idam_key_id
        self._sync_auth_api_key_record(record)
        created = {
            "key_id": record.key_id,
            "token": record.token,
            "label": record.label,
            "roles": sorted(record.roles),
            "capabilities": sorted(record.capabilities),
            "user_id": record.user_id,
            "revoked": record.revoked,
        }
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="create",
            target_type="api_key",
            target_id=key_id,
            target_name=record.label,
            new_value={k: v for k, v in created.items() if k != "token"},
            user_id=record.user_id,
        )
        self._emit_config_event(
            entity_type="api_key",
            entity_id=key_id,
            action="created",
            actor=actor,
            payload={k: v for k, v in created.items() if k != "token"},
        )
        return created

    def admin_api_key_revoke(self, key_id: str, roles: set[str], actor: str = "admin") -> dict[str, Any]:
        """Revoke an API key record."""
        self._require_admin(roles)
        if key_id not in self.api_keys:
            raise KeyError(key_id)
        record = self.api_keys[key_id]
        record.revoked = True
        idam_key_id = self._idam_api_key_refs.get(key_id, "")
        if self._idam_api_keys is not None and idam_key_id:
            self._idam_api_keys.revoke(idam_key_id)
        self._sync_auth_api_key_record(record)
        result = {
            "key_id": record.key_id,
            "label": record.label,
            "revoked": record.revoked,
        }
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="revoke",
            target_type="api_key",
            target_id=key_id,
            target_name=record.label,
            prior_value={
                "key_id": record.key_id,
                "label": record.label,
                "roles": sorted(record.roles),
                "capabilities": sorted(record.capabilities),
                "user_id": record.user_id,
                "revoked": False,
            },
            new_value=result,
            user_id=record.user_id,
        )
        self._emit_config_event(
            entity_type="api_key",
            entity_id=key_id,
            action="revoked",
            actor=actor,
            payload=result,
        )
        return result

    def a2a_config_events(self) -> list[dict[str, Any]]:
        """Return emitted configuration events for the A2A interface."""
        return [
            {
                "event_id": item.event_id,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "action": item.action,
                "actor": item.actor,
                "payload": item.payload,
                "created_at": item.created_at.isoformat(),
            }
            for item in reversed(self.a2a_events)
        ]

    def collections_list(self, profile: str) -> list[str]:
        """Execute collections list."""
        output = [
            record.collection
            for record in self.collections.values()
            if record.profile == profile
        ]
        return sorted(set(output))

    def collection_get(self, profile: str, collection: str) -> dict[str, Any]:
        """Return collection details for the requested profile and name."""
        collection_key = self._collection_key(profile, collection)
        if collection_key not in self.collections:
            raise KeyError(collection_key)
        return self._collection_payload(self._ensure_collection_record(profile, collection))

    def admin_collection_create(
        self,
        profile: str,
        collection: str,
        roles: set[str],
        payload: dict[str, Any] | None = None,
        allowed_roles: set[str] | None = None,
        actor: str = "admin",
    ) -> None:
        """Execute admin collection create."""
        # Covers: FR-16
        self._require_admin(roles)
        collection_key = self._collection_key(profile, collection)
        backend_binding_pending = False
        if self._async_job_execution:
            try:
                provider_id = self._profile_provider(profile)
                backend_name = self._backend_collection_name(profile, collection, provider_id=provider_id)
                existing = self._run_async(self.vdb.get_collection(backend_name, provider_id=provider_id))
                backend_binding_pending = existing is None
            except Exception:
                backend_binding_pending = True
        else:
            try:
                self._ensure_backend_collection(profile, collection)
            except KeyError:
                backend_binding_pending = True
        resolved_payload = dict(payload or {})
        metadata_payload = (
            dict(resolved_payload.get("metadata", {}))
            if isinstance(resolved_payload.get("metadata"), dict)
            else {}
        )
        if backend_binding_pending:
            metadata_payload.setdefault("backend_binding_pending", True)
        resolved_allowed_roles = set(allowed_roles or resolved_payload.get("allowed_roles") or {"reader", "writer", "maintainer", "admin"})
        record = CollectionRecord(
            profile=profile,
            collection=collection,
            description=str(resolved_payload.get("description", "")),
            dimensions=int(resolved_payload["dimensions"]) if resolved_payload.get("dimensions") not in {None, ""} else None,
            distance_metric=str(resolved_payload.get("distance_metric", "cosine") or "cosine"),
            metadata=metadata_payload,
            allowed_roles=resolved_allowed_roles,
        )
        self.collections[collection_key] = record
        self.collection_roles[collection_key] = set(record.allowed_roles)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="create",
            target_type="collection",
            target_id=collection_key,
            target_name=collection,
            new_value=self._collection_payload(record),
            profile=profile,
            collection=collection,
        )
        self._emit_config_event(
            entity_type="collection",
            entity_id=collection_key,
            action="created",
            actor=actor,
            payload=self._collection_payload(record),
        )

    def admin_collection_update(
        self,
        profile: str,
        collection: str,
        roles: set[str],
        updates: dict[str, Any],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Update collection metadata and RBAC details."""
        self._require_admin(roles)
        collection_key = self._collection_key(profile, collection)
        if collection_key not in self.collections:
            raise KeyError(collection_key)
        record = self._ensure_collection_record(profile, collection)
        prior_value = self._collection_payload(record)
        if "description" in updates:
            record.description = str(updates.get("description", ""))
        if "dimensions" in updates:
            raw_dimensions = updates.get("dimensions")
            record.dimensions = int(raw_dimensions) if raw_dimensions not in {None, ""} else None
        if "distance_metric" in updates:
            record.distance_metric = str(updates.get("distance_metric") or "cosine")
        if "metadata" in updates and isinstance(updates.get("metadata"), dict):
            record.metadata = dict(updates["metadata"])
        if "allowed_roles" in updates and isinstance(updates.get("allowed_roles"), list):
            record.allowed_roles = set(str(item) for item in updates["allowed_roles"] if str(item).strip())
            if not record.allowed_roles:
                raise ValueError("allowed_roles must not be empty")
            self.collection_roles[collection_key] = set(record.allowed_roles)
        payload = self._collection_payload(record)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="update",
            target_type="collection",
            target_id=collection_key,
            target_name=collection,
            prior_value=prior_value,
            new_value=payload,
            profile=profile,
            collection=collection,
        )
        self._emit_config_event(
            entity_type="collection",
            entity_id=collection_key,
            action="updated",
            actor=actor,
            payload=payload,
        )
        return payload

    def admin_collection_delete(self, profile: str, collection: str, roles: set[str], actor: str = "admin") -> None:
        """Execute admin collection delete."""
        self._require_admin(roles)
        collection_key = self._collection_key(profile, collection)
        prior_value = self._collection_payload(self._ensure_collection_record(profile, collection))
        try:
            self._run_async(
                self.vdb.delete_collection(
                    self._backend_collection_name(profile, collection, provider_id=self._profile_provider(profile)),
                    provider_id=self._profile_provider(profile),
                )
            )
        except Exception:
            # VDB backend may be unavailable or the collection may not exist
            # in VDB (backend_binding_pending). Proceed with in-memory removal.
            pass
        self.collection_roles.pop(collection_key, None)
        self.collections.pop(collection_key, None)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="delete",
            target_type="collection",
            target_id=collection_key,
            target_name=collection,
            prior_value=prior_value,
            profile=profile,
            collection=collection,
        )
        self._emit_config_event(
            entity_type="collection",
            entity_id=collection_key,
            action="deleted",
            actor=actor,
            payload={"profile": profile, "collection": collection},
        )

    def set_collection_roles(self, profile: str, collection: str, roles: set[str], allowed_roles: set[str]) -> None:
        """Set collection-level ACL roles for collection access checks."""
        self._require_admin(roles)
        if not allowed_roles:
            raise ValueError("allowed_roles must not be empty")
        collection_key = self._collection_key(profile, collection)
        self._ensure_backend_collection(profile, collection)
        self.collection_roles[collection_key] = set(allowed_roles)
        self._ensure_collection_record(profile, collection).allowed_roles = set(allowed_roles)

    def is_collection_role_allowed(self, profile: str, collection: str, roles: set[str]) -> bool:
        """Return True when caller roles are permitted for the collection."""
        collection_key = self._collection_key(profile, collection)
        allowed = self.collection_roles.get(collection_key)
        if allowed is None:
            return True
        return bool(set(roles).intersection(allowed))

    def ingest_text(
        self,
        profile: str,
        collection: str,
        text: str,
        source: str,
        actor: str,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> str:
        """Execute ingest text."""
        # Covers: FR-08, FR-10, FR-14
        if profile not in self.profiles:
            raise ValueError(f"Unknown profile: {profile}")

        try:
            self._ensure_backend_collection(profile, collection)
        except KeyError:
            record = self._ensure_collection_record(profile, collection)
            record.metadata.setdefault("backend_binding_pending", True)
        else:
            self._ensure_collection_record(profile, collection)

        source_key = f"{normalise_source_uri(source)}:{compute_content_hash(text)}"
        computed_key = self.queue.generate_idempotency_key(profile, collection, source_key)
        request_key = idempotency_key or computed_key
        if request_key in self.idempotency:
            return self.idempotency[request_key]

        queued_job = self.queue.enqueue(
            JobRecord(
                job_id=str(uuid4()),
                profile=profile,
                collection=collection,
                job_type="ingest_text",
                idempotency_key=request_key,
                server_id=self.queue.server_id,
            ),
            payload={
                "profile": profile,
                "collection": collection,
                "text": text,
                "source": source,
                "actor": actor,
                "metadata": metadata or {},
                "created_at": created_at.isoformat() if created_at is not None else "",
            },
            actor=actor,
        )
        self._dispatch_job_async(queued_job.job_id)
        self.idempotency[request_key] = queued_job.job_id
        return queued_job.job_id

    def ingest_reference(self, profile: str, collection: str, path: str, actor: str) -> str:
        """Execute ingest reference.

        W28C-427 IDX-SNAG-004: routes through the connector resolver so
        HTTP, S3, WebDAV, FTP, GDrive, and filesystem URIs are all supported.
        Falls back to direct path_utils.read_bytes for plain filesystem paths.
        """
        # Covers: FR-08
        try:
            from index_tools.connectors.resolver import resolve_source, fetch_source
            plan = resolve_source(path)
            payload = fetch_source(plan)
        except (ValueError, NotImplementedError):
            # Fallback for plain local paths or unsupported schemes
            payload = path_utils.read_bytes(path)
        return self.ingest_text(
            profile=profile,
            collection=collection,
            text=payload.decode("utf-8", errors="replace"),
            source=path,
            actor=actor,
        )

    def ingest_upload(
        self,
        profile: str,
        collection: str,
        filename: str,
        content: bytes,
        actor: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ingest uploaded browser file content through the same runtime path as text ingest."""
        source_uri = f"upload://{filename}"
        payload = dict(metadata or {})
        payload.setdefault("filename", filename)
        payload.setdefault("mime_type", _infer_mime_type(filename))
        job_id = self.ingest_text(
            profile=profile,
            collection=collection,
            text=content.decode("utf-8", errors="replace"),
            source=source_uri,
            actor=actor,
            metadata=payload,
        )
        return {
            "job_id": job_id,
            "filename": filename,
            "source": source_uri,
        }

    def source_configs_list(self) -> list[dict[str, Any]]:
        """Return all saved source configuration entries."""
        return [self.source_config_get(source_id) for source_id in sorted(self.source_configs.keys())]

    def source_config_get(self, source_id: str) -> dict[str, Any]:
        """Return one saved source configuration entry."""
        return self._source_config_payload(self.source_configs[source_id])

    def admin_source_config_create(
        self,
        source_id: str,
        roles: set[str],
        payload: dict[str, Any],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Create a saved source configuration entry."""
        self._require_admin(roles)
        if source_id in self.source_configs:
            raise ValueError(f"Source config already exists: {source_id}")
        record = SourceConfigRecord(
            source_id=source_id,
            source_type=str(payload.get("source_type", "filesystem") or "filesystem"),
            uri=str(payload.get("uri", "")),
            schedule=str(payload.get("schedule", "")),
            profile=str(payload.get("profile", "default")),
            collection=str(payload.get("collection", "w12_documents")),
            enabled=bool(payload.get("enabled", True)),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata"), dict) else {},
        )
        self.source_configs[source_id] = record
        serialised = self._source_config_payload(record)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="create",
            target_type="source_config",
            target_id=source_id,
            target_name=source_id,
            new_value=serialised,
            profile=record.profile,
            collection=record.collection,
        )
        self._emit_config_event(
            entity_type="source_config",
            entity_id=source_id,
            action="created",
            actor=actor,
            payload=serialised,
        )
        return serialised

    def admin_source_config_update(
        self,
        source_id: str,
        roles: set[str],
        payload: dict[str, Any],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Update a saved source configuration entry."""
        self._require_admin(roles)
        if source_id not in self.source_configs:
            raise KeyError(source_id)
        record = self.source_configs[source_id]
        prior_value = self._source_config_payload(record)
        if "source_type" in payload:
            record.source_type = str(payload.get("source_type") or "filesystem")
        if "uri" in payload:
            record.uri = str(payload.get("uri") or "")
        if "schedule" in payload:
            record.schedule = str(payload.get("schedule") or "")
        if "profile" in payload:
            record.profile = str(payload.get("profile") or "default")
        if "collection" in payload:
            record.collection = str(payload.get("collection") or "w12_documents")
        if "enabled" in payload:
            record.enabled = bool(payload.get("enabled"))
        if "metadata" in payload and isinstance(payload.get("metadata"), dict):
            record.metadata = dict(payload["metadata"])
        serialised = self._source_config_payload(record)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="update",
            target_type="source_config",
            target_id=source_id,
            target_name=source_id,
            prior_value=prior_value,
            new_value=serialised,
            profile=record.profile,
            collection=record.collection,
        )
        self._emit_config_event(
            entity_type="source_config",
            entity_id=source_id,
            action="updated",
            actor=actor,
            payload=serialised,
        )
        return serialised

    def admin_source_config_delete(self, source_id: str, roles: set[str], actor: str = "admin") -> None:
        """Delete a saved source configuration entry."""
        self._require_admin(roles)
        prior_value = self.source_config_get(source_id)
        if self.source_configs.pop(source_id, None) is None:
            raise KeyError(source_id)
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="delete",
            target_type="source_config",
            target_id=source_id,
            target_name=source_id,
            prior_value=prior_value,
        )
        self._emit_config_event(
            entity_type="source_config",
            entity_id=source_id,
            action="deleted",
            actor=actor,
            payload={"source_id": source_id},
        )

    def rbac_bindings_list(self) -> list[dict[str, Any]]:
        """Return current RBAC bindings derived from user and group role assignments."""
        bindings: list[dict[str, Any]] = []
        for user_id, record in sorted(self.users.items()):
            for role in sorted(record.roles):
                bindings.append({"entity_type": "user", "entity_id": user_id, "role": role})
        for group_id, record in sorted(self.groups.items()):
            for role in sorted(record.roles):
                bindings.append({"entity_type": "group", "entity_id": group_id, "role": role})
        return bindings

    def admin_rbac_bind(
        self,
        entity_type: str,
        entity_id: str,
        role: str,
        roles: set[str],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Bind a role to a user or group."""
        self._require_admin(roles)
        target_role = str(role).strip()
        if not target_role:
            raise ValueError("role is required")
        if entity_type == "user":
            if entity_id not in self.users:
                raise KeyError(entity_id)
            self.users[entity_id].roles.add(target_role)
            self._sync_idam_user(entity_id)
            self._refresh_auth_api_keys_for_user(entity_id)
        elif entity_type == "group":
            if entity_id not in self.groups:
                raise KeyError(entity_id)
            self.groups[entity_id].roles.add(target_role)
            self._sync_idam_group(entity_id)
            self._refresh_auth_api_keys_for_group(entity_id)
        else:
            raise ValueError(f"Unsupported RBAC entity type: {entity_type}")
        binding = {"entity_type": entity_type, "entity_id": entity_id, "role": target_role}
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="bind",
            target_type="rbac",
            target_id=f"{entity_type}:{entity_id}:{target_role}",
            target_name=f"{entity_type}:{entity_id}",
            new_value=binding,
        )
        self._emit_config_event(
            entity_type="rbac_binding",
            entity_id=f"{entity_type}:{entity_id}",
            action="bound",
            actor=actor,
            payload=binding,
        )
        return binding

    def admin_rbac_unbind(
        self,
        entity_type: str,
        entity_id: str,
        role: str,
        roles: set[str],
        actor: str = "admin",
    ) -> dict[str, Any]:
        """Unbind a role from a user or group."""
        self._require_admin(roles)
        target_role = str(role).strip()
        if entity_type == "user":
            if entity_id not in self.users:
                raise KeyError(entity_id)
            self.users[entity_id].roles.discard(target_role)
            self._sync_idam_user(entity_id)
            self._refresh_auth_api_keys_for_user(entity_id)
        elif entity_type == "group":
            if entity_id not in self.groups:
                raise KeyError(entity_id)
            self.groups[entity_id].roles.discard(target_role)
            self._sync_idam_group(entity_id)
            self._refresh_auth_api_keys_for_group(entity_id)
        else:
            raise ValueError(f"Unsupported RBAC entity type: {entity_type}")
        binding = {"entity_type": entity_type, "entity_id": entity_id, "role": target_role}
        self.audit_logger.log_admin_action(
            actor=actor,
            roles=roles,
            action="unbind",
            target_type="rbac",
            target_id=f"{entity_type}:{entity_id}:{target_role}",
            target_name=f"{entity_type}:{entity_id}",
            prior_value=binding,
        )
        self._emit_config_event(
            entity_type="rbac_binding",
            entity_id=f"{entity_type}:{entity_id}",
            action="unbound",
            actor=actor,
            payload=binding,
        )
        return binding

    def _profile_backend(self, profile: str) -> str:
        profile_data = self.profiles.get(profile, self.profiles["default"])
        backend = str(profile_data.get("backend", self._default_backend)).strip().lower()
        return backend or self._default_backend

    def _build_capability_descriptor(
        self,
        profile: str,
        capability_override: dict[str, Any] | None = None,
    ) -> Any | None:
        if CapabilityDescriptor is None:
            return None
        payload: dict[str, Any] = {
            "provider_id": self._profile_backend(profile),
            "filtering": True,
            "hybrid_search": False,
            "sparse_vectors": False,
            "multi_vector": False,
            "metadata_indexing": True,
            "upsert_semantics": True,
            "delete_by_filter": True,
            "ttl_native": False,
            "transactions": False,
            "consistency": False,
            "max_metadata_bytes": 65536,
            "max_batch_size": 1000,
            "supports_multimodal": False,
        }
        if capability_override:
            payload.update(capability_override)
        return CapabilityDescriptor(**payload)

    def _get_document_record(
        self,
        doc_id: str,
        profile: str | None = None,
        collection: str | None = None,
    ) -> DocumentRecord:
        """Return a stored document record.

        A123 fix: optional ``profile`` / ``collection`` scope the lookup so
        we never surface a record from a different profile when the same
        record_id (deterministic hash of doc_id+chunk_index) was used for
        parallel ingests across two backends. When the caller does not
        supply these (legacy path, internal reindex/delete, A2A skill where
        the contract is doc_id-only), we keep the historical
        first-match-wins behaviour for backward compatibility.
        """
        def _matches_scope(rec: DocumentRecord) -> bool:
            if profile is not None and rec.profile != profile:
                return False
            if collection is not None and rec.collection != collection:
                return False
            return True

        record = self.documents.get(doc_id)
        if record is not None and _matches_scope(record):
            return record
        for candidate in self.documents.values():
            if not (
                candidate.doc_id == doc_id
                or str(candidate.metadata.get("doc_id", "")) == doc_id
                or candidate.record_id == doc_id
            ):
                continue
            if _matches_scope(candidate):
                return candidate
        raise KeyError(doc_id)

    @staticmethod
    def _search_result_payload(
        *,
        record_id: str,
        text: str,
        score: float,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        canonical_record_id = str(metadata.get("record_id") or record_id)
        canonical_doc_id = str(metadata.get("doc_id") or canonical_record_id)
        return {
            "doc_id": canonical_doc_id,
            "record_id": canonical_record_id,
            "chunk_id": str(metadata.get("chunk_id") or canonical_record_id),
            "text": text,
            "score": float(score),
            "source_uri": str(metadata.get("source_uri", "")),
            "content_hash": str(metadata.get("content_hash", "")),
            "lifecycle_state": str(metadata.get("lifecycle_state", "active")),
            "is_latest": metadata.get("is_latest"),
            "metadata": metadata,
        }

    def backend_capabilities(
        self,
        profile: str = "default",
        capability_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        descriptor = self._build_capability_descriptor(profile, capability_override)
        if descriptor is None:
            return {
                "provider_id": self._profile_backend(profile),
                "filtering": True,
                "max_batch_size": 1000,
            }
        return _descriptor_to_dict(descriptor)

    def search_plan(
        self,
        profile: str,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        capability_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Covers: FR-13A
        checked_filters = dict(filters or {})
        descriptor = self._build_capability_descriptor(profile, capability_override)
        if descriptor is None or vdb_plan_search is None or SearchRequest is None:
            if checked_filters and capability_override and not bool(capability_override.get("filtering", True)):
                raise ValueError("Backend capabilities do not support metadata filters")
            return {"mode": "vector", "top_k": max(1, int(top_k)), "filters": checked_filters}

        request = SearchRequest(query_text=query, top_k=max(1, int(top_k)), filters=checked_filters)
        planned = dict(vdb_plan_search(request, descriptor))
        if checked_filters and not planned.get("filters"):
            raise ValueError("Backend capabilities do not support metadata filters")
        return planned

    def search(
        self,
        profile: str,
        collection: str,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Execute search."""
        # Covers: FR-14
        planned = self.search_plan(profile=profile, query=query, top_k=top_k, filters=filters)
        requested_filters = dict(filters or {})
        resolved_filters = dict(planned.get("filters", filters or {}))
        filter_latest_only = "is_latest" not in requested_filters
        if SearchRequest is None:
            raise RuntimeError("cloud_dog_vdb SearchRequest is required")
        response = self._run_async(
                self.vdb.search(
                self._backend_collection_name(profile, collection, provider_id=self._profile_provider(profile)),
                SearchRequest(
                    query_text=query,
                    top_k=int(planned.get("top_k", top_k)),
                    filters=resolved_filters,
                    score_threshold=score_threshold,
                ),
                provider_id=self._profile_provider(profile),
            )
        )
        if not response.results:
            return self._local_search_results(
                profile=profile,
                collection=collection,
                query=query,
                top_k=int(planned.get("top_k", top_k)),
                filters=requested_filters or resolved_filters,
            )
        output: list[dict[str, Any]] = []
        for item in response.results:
            payload = dict(item.payload)
            record_id = str(item.id)
            local_record = self.documents.get(record_id)
            metadata = dict(payload.get("metadata", {}))
            text_value = str(payload.get("content", ""))
            if local_record is not None and local_record.profile == profile and local_record.collection == collection:
                metadata = dict(local_record.metadata)
                text_value = local_record.text
            if requested_filters and not self._metadata_matches_filters(metadata, requested_filters):
                continue
            if str(metadata.get("lifecycle_state", "active")) == "deleted":
                continue
            if filter_latest_only and metadata.get("is_latest") is False:
                continue
            output.append(
                self._search_result_payload(
                    record_id=record_id,
                    text=text_value,
                    score=float(item.score),
                    metadata=metadata,
                )
            )
        return output[: max(1, int(planned.get("top_k", top_k)))]

    @staticmethod
    def _metadata_matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        canonical_filters: dict[str, Any] = {
            key: value
            for key, value in filters.items()
            if (key in SCALAR_FILTER_FIELDS or key == "access_tags")
            and not isinstance(value, dict)
            and not (isinstance(value, str) and any(token in value for token in ("*", "?")))
        }
        if canonical_filters and not matches_metadata(metadata, canonical_filters):
            return False
        for key, expected in filters.items():
            if key in canonical_filters:
                continue
            actual = metadata.get(key)
            if isinstance(expected, str) and isinstance(actual, str) and any(token in expected for token in ("*", "?")):
                if not fnmatch.fnmatch(actual, expected):
                    return False
                continue
            if isinstance(expected, (list, tuple, set)):
                if actual not in expected:
                    return False
                continue
            if isinstance(expected, dict):
                if not _metadata_operator_match(actual, expected):
                    return False
                continue
            if actual != expected:
                return False
        return True

    def _local_search_results(
        self,
        *,
        profile: str,
        collection: str,
        query: str,
        top_k: int,
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        query_text = query.strip().lower()
        if not query_text:
            return []

        terms = [term for term in re.findall(r"[a-z0-9]+", query_text) if term]
        if not terms:
            terms = [query_text]

        rows_with_order: list[tuple[float, float, dict[str, Any]]] = []
        for record in self.documents.values():
            if record.profile != profile or record.collection != collection:
                continue
            if str(record.metadata.get("lifecycle_state", "active")) == "deleted":
                continue
            if record.metadata.get("is_latest") is False:
                continue
            if filters and not self._metadata_matches_filters(record.metadata, filters):
                continue

            haystack = " ".join(
                [
                    record.text,
                    str(record.source),
                    json.dumps(record.metadata, sort_keys=True, ensure_ascii=True),
                ]
            ).lower()
            if not haystack:
                continue

            if query_text in haystack:
                overlap = len(terms)
            else:
                overlap = sum(1 for term in terms if term in haystack)
                if overlap == 0:
                    continue

            score = overlap / max(1, len(terms))
            rows_with_order.append(
                (
                    score,
                    record.created_at.timestamp(),
                    self._search_result_payload(
                        record_id=str(record.record_id or record.doc_id),
                        text=record.text,
                        score=float(score),
                        metadata=dict(record.metadata),
                    ),
                )
            )

        rows_with_order.sort(key=lambda item: (-item[0], -item[1], str(item[2]["doc_id"])))
        return [payload for _score, _created, payload in rows_with_order[: max(1, top_k)]]

    def retrieve(
        self,
        doc_id: str,
        profile: str | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Execute retrieve.

        A123 fix: when ``profile`` and/or ``collection`` are supplied (the
        canonical case from /api/v1/tools/retrieve via RetrieveInput), the
        record returned MUST belong to that profile/collection. Previously
        the handler ignored those arguments and returned whichever record
        the in-memory ``self.documents`` happened to hold under the doc_id —
        which is keyed by record_id and therefore overwrites identical
        chunks ingested under different profiles. That caused chroma-profile
        retrieves to surface qdrant-profile records (A117 §10 row 3).
        """
        record = self._get_document_record(doc_id, profile=profile, collection=collection)
        return {
            "doc_id": record.doc_id,
            "record_id": record.record_id or record.doc_id,
            "profile": record.profile,
            "collection": record.collection,
            "source": record.source,
            "source_uri": str(record.metadata.get("source_uri", record.source)),
            "text": record.text,
            "content_hash": str(record.metadata.get("content_hash", "")),
            "lifecycle_state": str(record.metadata.get("lifecycle_state", "active")),
            "is_latest": record.metadata.get("is_latest"),
            "metadata": record.metadata,
        }

    def delete_by_id(self, profile: str, collection: str, doc_id: str) -> bool:
        """Execute delete by id."""
        try:
            record = self._get_document_record(doc_id)
        except KeyError:
            record = None
        record_id = str(record.record_id or record.doc_id) if record is not None else doc_id
        deleted = bool(
            self._run_async(
                self.vdb.delete_record(
                    self._backend_collection_name(profile, collection, provider_id=self._profile_provider(profile)),
                    record_id,
                    provider_id=self._profile_provider(profile),
                )
            )
        )
        if record is not None and record.profile == profile and record.collection == collection:
            record.metadata.update(mark_deleted(record.metadata))
            _apply_metadata_pack_aliases(record.metadata)
            return True
        return deleted

    def delete_by_filter(self, profile: str, collection: str, filters: dict[str, Any]) -> int:
        """Execute delete by filter."""
        matched_records = [
            value
            for value in self.documents.values()
            if value.profile == profile
            and value.collection == collection
            and str(value.metadata.get("lifecycle_state", "active")) != "deleted"
            and self._metadata_matches_filters(value.metadata, filters)
        ]
        deleted = int(
            self._run_async(
                self.vdb.delete_by_filter(
                    self._backend_collection_name(profile, collection, provider_id=self._profile_provider(profile)),
                    filters,
                    provider_id=self._profile_provider(profile),
                )
            )
        )
        for value in matched_records:
            value.metadata.update(mark_deleted(value.metadata))
            _apply_metadata_pack_aliases(value.metadata)
        return max(deleted, len(matched_records))

    def retention_run(self, profile: str, collection: str, older_than_days: int) -> int:
        """Execute retention run."""
        # Covers: FR-16
        threshold = datetime.now(timezone.utc) - timedelta(days=older_than_days)  # noqa: UP017
        deleted_count = 0
        for value in list(self.documents.values()):
            if str(value.metadata.get("lifecycle_state", "active")) == "archived":
                continue
            if (
                value.profile == profile
                and value.collection == collection
                and value.created_at < threshold
                and self.delete_by_id(profile, collection, value.record_id or value.doc_id)
            ):
                deleted_count += 1
        return deleted_count

    def reindex_run(self, profile: str, collection: str) -> dict[str, int]:
        """Execute reindex run."""
        doc_count = int(
            self._run_async(
                self.vdb.count_documents(
                    self._backend_collection_name(profile, collection, provider_id=self._profile_provider(profile)),
                    provider_id=self._profile_provider(profile),
                )
            )
        )
        return {"documents": doc_count}

    def job_list(self, limit: int | None = None) -> list[JobRecord]:
        """Execute job list."""
        return self.queue.list_jobs(limit=limit)

    def job_get(self, job_id: str) -> JobRecord:
        """Execute job get."""
        return self.queue.get(job_id)

    def job_wait(self, job_id: str) -> JobRecord:
        """Execute job wait."""
        return self.queue.wait(job_id)

    def job_cancel(self, job_id: str) -> JobRecord:
        """Execute job cancel."""
        return self.queue.cancel(job_id)

    def job_retry(self, job_id: str) -> JobRecord:
        """Execute job retry."""
        job = self.queue.retry(job_id)
        if job.status is JobStatus.queued:
            self._dispatch_job_async(job_id)
            return self.queue.get(job_id)
        return job

    def queue_status(self) -> dict[str, Any]:
        """Execute queue status."""
        return self.queue.queue_status()

    def backend_health_check(self, provider_id: str | None = None) -> dict[str, str]:
        """Execute backend health check."""
        resolved_provider = (provider_id or self._default_backend).strip().lower()
        healthy = bool(self._run_async(self.vdb.health_check(provider_id=resolved_provider)))
        return {
            "status": "ok" if healthy else "error",
            "provider": resolved_provider,
            "backend": resolved_provider,
        }

    def embedding_health_check(self) -> dict[str, str | int]:
        """Execute embedding health check."""
        if not self._live_backend_mode:
            vectors = self.embedding_adapter.embed(["health check"])
            dims = len(vectors[0]) if vectors else 0
            return {
                "status": "ok" if dims > 0 else "error",
                "provider": self._llm_provider,
                "model": self._llm_model,
                "dimensions": dims,
            }
        if self._llm_client is None:
            return {"status": "error", "provider": self._llm_provider, "model": self._llm_model, "dimensions": 0}
        try:
            from cloud_dog_config import get_config
            healthy = bool(self._run_async(asyncio.wait_for(self._llm_client.health(), timeout=float(get_config("llm.health_timeout_seconds") or 15.0))))
            dims = self._embedding_dimension_cache or 1024 if healthy else 0
            return {
                "status": "ok" if healthy else "error",
                "provider": self._llm_provider,
                "model": self._llm_model,
                "dimensions": dims,
            }
        except Exception:
            return {"status": "error", "provider": self._llm_provider, "model": self._llm_model, "dimensions": 0}

    # -- PS-78 File Lifecycle (W28C-427 IDX-SNAG-002) --

    def file_upload(self, filename: str, content: bytes | str, *, profile: str = "default", actor: str = "system", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Upload a file to service storage. Returns file_id and metadata."""
        import base64
        from hashlib import sha256 as _sha256
        raw = content if isinstance(content, bytes) else (base64.b64decode(content) if content.startswith(("data:", "base64:")) or len(content) > 200 else content.encode("utf-8"))
        file_id = _sha256(raw).hexdigest()[:24]
        record = {
            "file_id": file_id,
            "filename": filename,
            "profile": profile,
            "size_bytes": len(raw),
            "content_hash": _sha256(raw).hexdigest(),
            "actor": actor,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        self._stored_files[file_id] = {"record": record, "content": raw}
        self.audit_logger.log(
            event_type="file.upload",
            actor=actor,
            action="create",
            outcome="success",
            target_type="file",
            target_id=file_id,
            details={"filename": filename, "size_bytes": len(raw), "profile": profile},
        )
        return record

    def file_list(self, *, profile: str | None = None) -> list[dict[str, Any]]:
        """List stored files, optionally filtered by profile."""
        results = []
        for fid, entry in self._stored_files.items():
            rec = entry["record"]
            if profile and rec.get("profile") != profile:
                continue
            results.append(rec)
        return results

    def file_get(self, file_id: str) -> dict[str, Any]:
        """Get metadata for a stored file by ID."""
        entry = self._stored_files.get(file_id)
        if entry is None:
            raise KeyError(f"File not found: {file_id}")
        return entry["record"]

    def file_download(self, file_id: str) -> dict[str, Any]:
        """Download stored file content by ID. Returns base64-encoded content."""
        import base64
        entry = self._stored_files.get(file_id)
        if entry is None:
            raise KeyError(f"File not found: {file_id}")
        content_b64 = base64.b64encode(entry["content"]).decode("ascii")
        return {
            **entry["record"],
            "content_base64": content_b64,
        }

    def file_delete(self, file_id: str, *, actor: str = "system") -> dict[str, str]:
        """Delete a stored file by ID."""
        entry = self._stored_files.pop(file_id, None)
        if entry is None:
            raise KeyError(f"File not found: {file_id}")
        self.audit_logger.log(
            event_type="file.delete",
            actor=actor,
            action="delete",
            outcome="success",
            target_type="file",
            target_id=file_id,
            details={"filename": entry["record"].get("filename", "")},
        )
        return {"file_id": file_id, "status": "deleted"}

    def _run_pipeline_preview(
        self,
        *,
        source: bytes | str,
        source_uri: str,
        parser_chain: list[str] | None = None,
        parser_options: dict[str, dict[str, Any]] | None = None,
        parser_services: dict[str, dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        ocr_mode: str = "disabled",
        ocr_provider: str = "",
        table_policy: str = "table_as_markdown",
        table_json_shape: str = "records",
        chunk_size: int = 800,
        chunk_overlap: int = 120,
    ) -> _PreviewResult:
        # Covers: FR-09, FR-13B
        if ingest_document is None or ParserIngestionOptions is None:
            raise ProviderDiagnosticError(
                operation="ingest_preview",
                provider="cloud_dog_vdb",
                message="VDB ingestion pipeline is unavailable",
                detail="cloud_dog_vdb ingestion modules are not importable",
            )

        filename = _infer_filename(source_uri)
        mime_type = _infer_mime_type(filename)
        base_metadata = dict(metadata or {})
        base_metadata.setdefault("source_uri", source_uri)
        base_metadata.setdefault("filename", filename)
        base_metadata.setdefault("mime_type", mime_type)
        chain = list(parser_chain or ["internal"])
        options = ParserIngestionOptions(
            parser_chain=chain,
            parser_options=parser_options or {},
            ocr_mode=ocr_mode,
            ocr_provider=ocr_provider,
            table_policy=table_policy,
            table_json_shape=table_json_shape,
            chunk_size=max(32, int(chunk_size)),
            chunk_overlap=max(0, int(chunk_overlap)),
        )

        bridge = _PreviewVdbBridge()
        checkpoints: list[dict[str, Any]] = []
        try:
            record_ids = _run_async_blocking(
                ingest_document(
                    bridge,
                    "__preview__",
                    source,
                    source_uri=source_uri,
                    options=options,
                    metadata=base_metadata,
                    parser_services=parser_services,
                    on_checkpoint=lambda stage, count: checkpoints.append({"stage": stage, "count": int(count)}),
                )
            )
        except Exception as exc:
            raise ProviderDiagnosticError(
                operation="ingest_preview",
                provider=",".join(chain),
                message="Provider parsing/ingestion failed",
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc

        chunks = [str(getattr(record, "content", "")) for record in bridge.records]
        first_metadata = dict(getattr(bridge.records[0], "metadata", {})) if bridge.records else base_metadata
        first_metadata = _normalise_provenance_metadata(first_metadata)
        return _PreviewResult(
            record_ids=[str(item) for item in record_ids],
            metadata=first_metadata,
            chunks=chunks,
            checkpoints=checkpoints,
        )

    def parsers_list(self, parser_services: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """List parser providers exposed by cloud_dog_vdb."""
        if build_parser_registry is None:
            return []
        registry = build_parser_registry(parser_services)
        output: list[dict[str, Any]] = []
        for provider_id in registry.list_ids():
            provider = registry.get(provider_id)
            if provider is None:
                continue
            output.append(
                {
                    "provider_id": provider.provider_id,
                    "provider_version": provider.provider_version,
                    "capabilities": _descriptor_to_dict(provider.capabilities),
                }
            )
        return output

    def parser_test(
        self,
        provider_id: str,
        *,
        sample_text: str = "parser health check",
        source_uri: str = "inline://parser-test.txt",
        parser_services: dict[str, dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run provider health and parse probe through cloud_dog_vdb parser surfaces."""
        if build_parser_registry is None:
            raise ProviderDiagnosticError(
                operation="parser_test",
                provider=provider_id,
                message="Parser registry is unavailable",
                detail="cloud_dog_vdb parser registry import failed",
            )
        registry = build_parser_registry(parser_services)
        provider = registry.get(provider_id)
        if provider is None:
            raise ValueError(f"Unknown parser provider: {provider_id}")

        filename = _infer_filename(source_uri)
        mime_type = _infer_mime_type(filename)
        try:
            healthy, ir = _run_async_blocking(
                _parser_probe(
                    provider=provider,
                    sample_text=sample_text,
                    filename=filename,
                    source_uri=source_uri,
                    mime_type=mime_type,
                    options=options or {},
                )
            )
        except Exception as exc:
            raise ProviderDiagnosticError(
                operation="parser_test",
                provider=provider_id,
                message="Provider parser test failed",
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc

        return {
            "provider_id": provider.provider_id,
            "provider_version": provider.provider_version,
            "healthy": bool(healthy),
            "text_blocks": len(getattr(ir, "text_blocks", [])),
            "table_blocks": len(getattr(ir, "table_blocks", [])),
            "quality": dict(getattr(ir, "quality", {})),
        }

    def ingest_preview(
        self,
        *,
        text: str,
        source_uri: str = "inline://preview.txt",
        parser_chain: list[str] | None = None,
        parser_options: dict[str, dict[str, Any]] | None = None,
        parser_services: dict[str, dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        ocr_mode: str = "disabled",
        ocr_provider: str = "",
        table_policy: str = "table_as_markdown",
        table_json_shape: str = "records",
    ) -> dict[str, Any]:
        """Run preview pipeline through cloud_dog_vdb without persisting project state."""
        # Covers: FR-P001
        preview = self._run_pipeline_preview(
            source=text.encode("utf-8"),
            source_uri=source_uri,
            parser_chain=parser_chain,
            parser_options=parser_options,
            parser_services=parser_services,
            metadata=metadata,
            ocr_mode=ocr_mode,
            ocr_provider=ocr_provider,
            table_policy=table_policy,
            table_json_shape=table_json_shape,
        )
        meta = dict(preview.metadata)
        return {
            "source_uri": meta.get("source_uri", source_uri),
            "filename": meta.get("filename", _infer_filename(source_uri)),
            "mime_type": meta.get("mime_type", _infer_mime_type(_infer_filename(source_uri))),
            "chunk_count": len(preview.chunks),
            "parser_provider": meta.get("parser_provider", ""),
            "parser_version": meta.get("parser_version", ""),
            "ocr_mode": meta.get("ocr_mode", ocr_mode),
            "ocr_engine": meta.get("ocr_engine", meta.get("ocr_provider", "")),
            "ocr_confidence": meta.get("ocr_confidence"),
            "ocr_applied": bool(meta.get("ocr_applied", False)),
            "page": meta.get("page", meta.get("page_number")),
            "table_id": meta.get("table_id", ""),
            "table_policy": meta.get("table_policy", table_policy),
            "checkpoints": preview.checkpoints,
        }

    def extract_only(
        self,
        *,
        text: str,
        source_uri: str = "inline://extract-only.txt",
        parser_chain: list[str] | None = None,
        parser_options: dict[str, dict[str, Any]] | None = None,
        parser_services: dict[str, dict[str, Any]] | None = None,
        ocr_mode: str = "disabled",
        ocr_provider: str = "",
        table_policy: str = "table_as_markdown",
        table_json_shape: str = "records",
    ) -> dict[str, Any]:
        """Parse/extract text only (no project state mutation) via cloud_dog_vdb."""
        preview = self._run_pipeline_preview(
            source=text.encode("utf-8"),
            source_uri=source_uri,
            parser_chain=parser_chain,
            parser_options=parser_options,
            parser_services=parser_services,
            ocr_mode=ocr_mode,
            ocr_provider=ocr_provider,
            table_policy=table_policy,
            table_json_shape=table_json_shape,
        )
        return {
            "source_uri": source_uri,
            "text": "\n\n".join(chunk for chunk in preview.chunks if chunk.strip()),
            "chunk_count": len(preview.chunks),
            "parser_provider": preview.metadata.get("parser_provider", ""),
            "ocr_applied": bool(preview.metadata.get("ocr_applied", False)),
            "table_policy": preview.metadata.get("table_policy", table_policy),
        }

    def ocr_run(
        self,
        *,
        text: str,
        mode: str = "auto",
        provider_id: str = "",
        min_chars: int = 200,
        min_scanned_ratio: float = 0.5,
        scanned_ratio: float = 0.0,
    ) -> dict[str, Any]:
        """Evaluate OCR planning through cloud_dog_vdb OCR planner."""
        if decide_ocr is None:
            enabled = mode == "force"
            reason = "mode_force" if enabled else "mode_disabled"
            return {"enabled": enabled, "mode": mode, "reason": reason, "provider_id": provider_id}
        decision = decide_ocr(
            mode=mode,
            text_chars=len(text),
            scanned_ratio=float(scanned_ratio),
            provider_id=provider_id,
            min_chars=max(1, int(min_chars)),
            min_scanned_ratio=float(min_scanned_ratio),
        )
        return {
            "enabled": bool(decision.enabled),
            "mode": decision.mode,
            "reason": decision.reason,
            "provider_id": decision.provider_id,
        }

    def table_extract(
        self,
        *,
        text: str,
        source_uri: str = "inline://table-extract.txt",
        parser_chain: list[str] | None = None,
        parser_options: dict[str, dict[str, Any]] | None = None,
        parser_services: dict[str, dict[str, Any]] | None = None,
        table_policy: str = "table_as_json",
        table_json_shape: str = "records",
    ) -> dict[str, Any]:
        """Run table extraction policy via cloud_dog_vdb parse/table pipeline."""
        preview = self._run_pipeline_preview(
            source=text.encode("utf-8"),
            source_uri=source_uri,
            parser_chain=parser_chain,
            parser_options=parser_options,
            parser_services=parser_services,
            table_policy=table_policy,
            table_json_shape=table_json_shape,
        )
        table_like = [
            chunk
            for chunk in preview.chunks
            if "|" in chunk or "<table" in chunk.lower() or ("{" in chunk and "}" in chunk)
        ]
        if not table_like and preview.chunks:
            table_like = [preview.chunks[0]]
        return {
            "source_uri": source_uri,
            "table_policy": table_policy,
            "table_json_shape": table_json_shape,
            "table_count": len(table_like),
            "tables": table_like,
            "parser_provider": preview.metadata.get("parser_provider", ""),
            "page": preview.metadata.get("page", preview.metadata.get("page_number")),
            "table_id": preview.metadata.get("table_id", ""),
        }

    def ingest_stream_session_start(self, profile: str, collection: str, ordering_key: str) -> str:
        """Create a stream-ingest session and return its session identifier."""
        # Covers: FR-15
        session_id = str(uuid4())
        self.stream_sessions[session_id] = StreamSession(
            session_id=session_id,
            profile=profile,
            collection=collection,
            ordering_key=ordering_key,
        )
        return session_id

    def ingest_stream_event(
        self,
        session_id: str,
        text: str,
        actor: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Execute ingest stream event."""
        session = self.stream_sessions[session_id]
        if session.closed:
            raise RuntimeError("Stream session is closed")
        job_id = self.ingest_text(
            profile=session.profile,
            collection=session.collection,
            text=text,
            source=f"stream://{session.ordering_key}",
            actor=actor,
            metadata=metadata,
        )
        session.ingested_events += 1
        session.job_ids.append(job_id)
        return job_id

    def ingest_stream_close(self, session_id: str) -> dict[str, Any]:
        """Execute ingest stream close."""
        session = self.stream_sessions[session_id]
        session.closed = True
        return {
            "session_id": session.session_id,
            "ingested_events": session.ingested_events,
            "job_ids": list(session.job_ids),
            "ordering_key": session.ordering_key,
        }


async def _parser_probe(
    *,
    provider: Any,
    sample_text: str,
    filename: str,
    source_uri: str,
    mime_type: str,
    options: dict[str, Any],
) -> tuple[bool, Any]:
    healthy = await provider.health_check()
    ir = await provider.parse_bytes(
        sample_text.encode("utf-8"),
        filename=filename,
        source_uri=source_uri,
        mime_type=mime_type,
        options=options,
    )
    return bool(healthy), ir


def _cfg(path: str, default: Any = None) -> Any:
    """Read a value from cloud_dog_config, returning *default* when absent.

    Accepts both dotted config paths (``index.db.url``) and env-var-style
    keys (``CLOUD_DOG__INDEX__DB__URL``) — the latter is converted automatically.
    """
    from cloud_dog_config import get_config  # type: ignore

    candidates = [path]
    converted = _env_key_to_config_path(path)
    if converted != path:
        candidates.append(converted)

    for candidate in candidates:
        try:
            value = get_config(candidate)
        except Exception:
            value = None
        if value is not None and str(value).strip():
            return value

    for candidate in candidates:
        try:
            value = _lookup_runtime_tree(candidate)
        except Exception:
            value = None
        if value is not None and str(value).strip():
            return value
    return default


def _env_key_to_config_path(key: str) -> str:
    """Convert an env var name to a cloud_dog_config dotted path.

    ``CLOUD_DOG__INDEX__EMBEDDING__PROVIDER`` → ``index.embedding.provider``
    ``EMBED_PROVIDER`` → ``embed_provider`` (lowercase, no transformation)
    """
    normalised = key.strip()
    if normalised.upper().startswith("CLOUD_DOG__"):
        normalised = normalised[len("CLOUD_DOG__"):]
    return normalised.replace("__", ".").lower()


def _required_env(*keys: str) -> str:
    """Read a required setting from cloud_dog_config using first non-empty key."""
    process_env = dict(os.environ)
    for key in keys:
        direct = str(process_env.get(key, "")).strip()
        if direct:
            return direct
        value = str(_cfg(key, "") or "").strip()
        if value:
            return value
    raise RuntimeError(f"Missing required configuration: {', '.join(keys)}")


def _resolve_queue_database_url(audit_path: str) -> str:
    """Resolve the queue database URL, defaulting to a per-instance SQLite file."""
    for path in ("INDEX_RETRIEVER_DB_URL", "DB_URL", "storage.db.url", "queue.database_url", "index.db.url", "db.url"):
        value = str(_cfg(path, "") or "").strip()
        if value.startswith("${") and value.endswith("}"):
            continue
        if value:
            return value
    base_path = path_utils.as_path(audit_path).with_suffix(".queue.db")
    _scheme = "sqlite+aiosqlite"
    _sep = ":///"
    return f"{_scheme}{_sep}{base_path}"


def _resolve_server_id() -> str:
    """Resolve the queue worker identity from runtime configuration."""
    for path in ("index.server_id", "service.server_id"):
        value = str(_cfg(path, "") or "").strip()
        if value:
            return value
    import socket
    return socket.gethostname() or "index-retriever-local"


def _resolve_environment() -> str:
    """Resolve the runtime environment name for structured audit events."""
    for path in ("service.environment", "environment"):
        value = str(_cfg(path, "") or "").strip()
        if value:
            return value.lower()
    return "dev"


def _env_or_default(key: str, default: str) -> str:
    """Return the configured string value or the supplied default."""
    value = str(_cfg(key, "") or "").strip()
    return value or default


def _env_int(key: str, *, default: int) -> int:
    """Return the configured integer value or the supplied default."""
    value = _cfg(key)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _env_float(key: str, *, default: float) -> float:
    """Return the configured float value or the supplied default."""
    value = _cfg(key)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _env_bool(key: str, *, default: bool) -> bool:
    """Return the configured boolean value or the supplied default."""
    value = _cfg(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
