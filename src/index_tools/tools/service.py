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
import json
import mimetypes
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import unquote, urlparse
from uuid import uuid4

from index_tools.audit.logger import AuditLogger
from index_tools.embeddings.adapter import EmbeddingAdapter
from index_tools.pipeline.chunking import token_chunks
from index_tools.pipeline.metadata import build_metadata
from index_tools.queue.engine import QueueEngine
from index_tools.queue.models import JobRecord, JobStatus
from index_tools.config.loader import runtime_env_files

try:
    from cloud_dog_config import load_config
except ImportError:  # pragma: no cover
    load_config = None  # type: ignore[assignment]

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


def _redact_diagnostic_detail(text: str) -> str:
    return _SECRET_FIELD_PATTERN.sub(r"\1=[REDACTED]", text)


def _descriptor_to_dict(descriptor: Any) -> dict[str, Any]:
    names = getattr(type(descriptor), "__dataclass_fields__", {})
    return {name: getattr(descriptor, name) for name in names}


def _infer_filename(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    candidate = parsed.path if parsed.scheme else source_uri
    return Path(unquote(candidate)).name or source_uri


def _infer_mime_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "text/plain"


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
    if load_config is None:
        return {}
    compiled = load_config(
        env_files=runtime_env_files(),
        defaults_yaml="defaults.yaml",
        unresolved_policy="strict",
        vault_enabled=True,
    )
    return _as_plain_data(compiled.data)


def _resolve_env_tier(runtime_tree: dict[str, Any]) -> str:
    explicit = str(os.environ.get("TEST_ENV_TIER", "")).strip().upper()
    if explicit:
        return explicit
    test_block = runtime_tree.get("test", {})
    if isinstance(test_block, dict):
        configured = str(test_block.get("env_tier", "")).strip().upper()
        if configured:
            return configured
    for env_file in runtime_env_files():
        name = Path(str(env_file)).name.upper()
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
        self._llm_provider = resolved_provider.strip().lower() or "ollama"
        self._llm_model = resolved_model
        self._embedding_dimension_cache: int | None = None
        self.vdb = self._build_vdb_client()
        self._llm_client = self._build_llm_client()
        resolved_queue_database_url = queue_database_url or _resolve_queue_database_url(audit_path)
        resolved_server_id = server_id or _resolve_server_id()
        self.queue = QueueEngine(
            database_url=resolved_queue_database_url,
            server_id=resolved_server_id,
            queue_name=_env_or_default("CLOUD_DOG__INDEX__QUEUE__NAME", "index-retriever"),
            timeout_seconds=_env_int("CLOUD_DOG__INDEX__QUEUE__DEFAULT_TIMEOUT_SECONDS", default=1800),
            retry_max_attempts=_env_int("CLOUD_DOG__INDEX__QUEUE__RETRY__MAX_ATTEMPTS", default=3),
            retry_backoff_seconds=_env_float("CLOUD_DOG__INDEX__QUEUE__RETRY__BACKOFF_SECONDS", default=5.0),
            redis_enabled=_env_bool("CLOUD_DOG__INDEX__QUEUE__REDIS__ENABLED", default=False),
            redis_url=_env_or_default("CLOUD_DOG__INDEX__QUEUE__REDIS__URL", ""),
        )
        self.audit_logger = AuditLogger(
            path=audit_path,
            server_id=self.queue.server_id,
            environment=_resolve_environment(),
        )
        self.embedding_adapter = EmbeddingAdapter(provider=resolved_provider, model=resolved_model)
        self.profiles: dict[str, dict[str, Any]] = {
            "default": {
                "enabled": True,
                "backend": self._default_backend,
                "roles": {"reader", "writer", "maintainer", "admin"},
            }
        }
        self.collections: dict[str, CollectionRecord] = {}
        self.collection_roles: dict[str, set[str]] = {}
        self.source_configs: dict[str, SourceConfigRecord] = {}
        self.documents: dict[str, DocumentRecord] = {}
        self.idempotency: dict[str, str] = {}
        self.stream_sessions: dict[str, StreamSession] = {}
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

    def _run_async(self, coro: Any) -> Any:
        if self._loop_thread is not None and self._loop_thread.is_alive():
            return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return self._loop.run_until_complete(coro)

        self._ensure_loop_thread()
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def _ensure_loop_thread(self) -> None:
        if self._loop_thread is not None and self._loop_thread.is_alive():
            return

        def _runner() -> None:
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._loop_thread = threading.Thread(target=_runner, name="index-service-async-loop", daemon=True)
        self._loop_thread.start()

    def _profile_provider(self, profile: str) -> str:
        payload = self.profiles.get(profile, self.profiles.get("default", {}))
        provider = str(payload.get("backend", self._default_backend)).strip().lower()
        return provider or self._default_backend

    def _build_vdb_client(self) -> Any:
        if get_vdb_client is None:
            raise RuntimeError("cloud_dog_vdb is required")

        profile_default = _nested_mapping(self._runtime_tree, "profiles", "default")
        profile_vdb = _nested_mapping(profile_default, "vdb")
        profile_chroma = _nested_mapping(profile_vdb, "chroma")
        index_vdb = _nested_mapping(self._runtime_tree, "index", "vdb")

        chroma_url = str(index_vdb.get("chroma_url", "")).strip()
        qdrant_url = str(index_vdb.get("qdrant_url", "")).strip()
        default_backend = self._default_backend
        vector_stores: dict[str, Any] = {"default_backend": default_backend}

        chroma_local_mode = not self._live_backend_mode or (
            str(profile_vdb.get("type", "")).strip().lower() == "chroma"
            and str(profile_chroma.get("mode", "")).strip().lower() == "local"
            and not chroma_url
        )
        if chroma_url or chroma_local_mode:
            vector_stores["chroma"] = {
                "enabled": True,
                "base_url": chroma_url,
                "timeout_seconds": 120,
                "local_mode": chroma_local_mode,
            }

        if qdrant_url:
            vector_stores["qdrant"] = {
                "enabled": True,
                "base_url": qdrant_url,
                "api_key": str(index_vdb.get("qdrant_api_key", "")).strip(),
                "timeout_seconds": 120,
                "local_mode": not self._live_backend_mode,
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
                        timeout=30.0,
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
        existing = self._run_async(self.vdb.get_collection(backend_name, provider_id=provider_id))
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
        return backend_name

    @staticmethod
    def _collection_key(profile: str, collection: str) -> str:
        """Internal helper to collection key."""
        return f"{profile}:{collection}"

    @staticmethod
    def _backend_collection_name(profile: str, collection: str, provider_id: str | None = None) -> str:
        """Return a backend-safe physical collection name for the VDB layer."""
        provider = str(provider_id or "").strip().lower()
        base_name = _safe_backend_name(f"indexretriever_{profile}_{collection}")
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
        """Execute the ingest pipeline for a queued job record."""
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
        provider_id = self._profile_provider(profile)
        backend_collection = self._backend_collection_name(profile, collection, provider_id=provider_id)
        doc_id = str(uuid4())
        chunks = token_chunks(text, chunk_size=64, chunk_overlap=8)
        if not chunks:
            chunks = [text]
        document_metadata = build_metadata(
            source=source,
            content=text.encode(),
            profile=profile,
            collection=collection,
        )
        if isinstance(metadata, dict):
            document_metadata.update(metadata)
        source_type = "file" if "://" in source else "other"
        created_value = (created_at or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")  # noqa: UP017
        document_metadata.setdefault("tenant_id", profile)
        document_metadata.setdefault("source", source)
        document_metadata.setdefault("source_uri", source)
        document_metadata.setdefault("source_type", source_type)
        document_metadata.setdefault("filename", _infer_filename(str(document_metadata["source_uri"])))
        document_metadata.setdefault("mime_type", _infer_mime_type(str(document_metadata["filename"])))
        document_metadata.setdefault("lifecycle_state", "active")
        document_metadata["created_at"] = str(document_metadata.get("created_at") or created_value).replace("+00:00", "Z")
        document_metadata.setdefault("actor", actor)
        document_metadata.setdefault("profile", profile)
        document_metadata.setdefault("collection", collection)
        document_metadata.setdefault("indexing_signature", self._llm_model)
        document_metadata.setdefault("embedding_model", self._llm_model)
        document_metadata.setdefault("chunker_version", "v1")

        self._run_async(
            self.vdb.upsert_records(
                backend_collection,
                [Record(record_id=doc_id, content=text, metadata=document_metadata)],
                provider_id=provider_id,
            )
        )
        created = created_at or datetime.now(timezone.utc)  # noqa: UP017
        self.documents[doc_id] = DocumentRecord(
            doc_id=doc_id,
            profile=profile,
            collection=collection,
            source=source,
            text=text,
            metadata=document_metadata,
            created_at=created,
        )

        self.audit_logger.log_ingest(
            actor=actor,
            profile=profile,
            collection=collection,
            job_id=job.job_id,
            source=source,
            metadata=metadata,
            chunk_count=len(chunks),
        )

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
        key_roles = set(str(item) for item in payload.get("roles", ["reader"]))
        record = ApiKeyRecord(
            key_id=key_id,
            token=token,
            label=str(payload.get("label", key_id)),
            roles=key_roles,
            capabilities=set(str(item) for item in payload.get("capabilities", [])),
            user_id=str(payload["user_id"]) if payload.get("user_id") else None,
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
            for item in self.a2a_events
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
        self._ensure_backend_collection(profile, collection)
        resolved_payload = dict(payload or {})
        resolved_allowed_roles = set(allowed_roles or resolved_payload.get("allowed_roles") or {"reader", "writer", "maintainer", "admin"})
        record = CollectionRecord(
            profile=profile,
            collection=collection,
            description=str(resolved_payload.get("description", "")),
            dimensions=int(resolved_payload["dimensions"]) if resolved_payload.get("dimensions") not in {None, ""} else None,
            distance_metric=str(resolved_payload.get("distance_metric", "cosine") or "cosine"),
            metadata=dict(resolved_payload.get("metadata", {})) if isinstance(resolved_payload.get("metadata"), dict) else {},
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
        self._run_async(
            self.vdb.delete_collection(
                self._backend_collection_name(profile, collection, provider_id=self._profile_provider(profile)),
                provider_id=self._profile_provider(profile),
            )
        )
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

        collection_key = self._ensure_backend_collection(profile, collection)
        self._ensure_collection_record(profile, collection)

        source_key = source + ":" + sha256(text.encode()).hexdigest()
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
        self.queue.run(job_id=queued_job.job_id)
        self.idempotency[request_key] = queued_job.job_id
        return queued_job.job_id

    def ingest_reference(self, profile: str, collection: str, path: str, actor: str) -> str:
        """Execute ingest reference."""
        # Covers: FR-08
        with open(path, "rb") as handle:
            payload = handle.read()
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
        if SearchRequest is None:
            raise RuntimeError("cloud_dog_vdb SearchRequest is required")
        response = self._run_async(
                self.vdb.search(
                self._backend_collection_name(profile, collection, provider_id=self._profile_provider(profile)),
                SearchRequest(
                    query_text=query,
                    top_k=int(planned.get("top_k", top_k)),
                    filters=dict(planned.get("filters", filters or {})),
                    score_threshold=score_threshold,
                ),
                provider_id=self._profile_provider(profile),
            )
        )
        output: list[dict[str, Any]] = []
        for item in response.results:
            payload = dict(item.payload)
            output.append(
                {
                    "doc_id": str(item.id),
                    "chunk_id": str(item.id),
                    "text": str(payload.get("content", "")),
                    "score": float(item.score),
                    "metadata": dict(payload.get("metadata", {})),
                }
            )
        return output

    def retrieve(self, doc_id: str) -> dict[str, Any]:
        """Execute retrieve."""
        record = self.documents[doc_id]
        return {
            "doc_id": record.doc_id,
            "profile": record.profile,
            "collection": record.collection,
            "source": record.source,
            "text": record.text,
            "metadata": record.metadata,
        }

    def delete_by_id(self, profile: str, collection: str, doc_id: str) -> bool:
        """Execute delete by id."""
        deleted = bool(
            self._run_async(
                self.vdb.delete_record(
                    self._backend_collection_name(profile, collection, provider_id=self._profile_provider(profile)),
                    doc_id,
                    provider_id=self._profile_provider(profile),
                )
            )
        )
        self.documents.pop(doc_id, None)
        return deleted

    def delete_by_filter(self, profile: str, collection: str, filters: dict[str, Any]) -> int:
        """Execute delete by filter."""
        deleted = int(
            self._run_async(
                self.vdb.delete_by_filter(
                    self._backend_collection_name(profile, collection, provider_id=self._profile_provider(profile)),
                    filters,
                    provider_id=self._profile_provider(profile),
                )
            )
        )
        if deleted:
            keep: dict[str, DocumentRecord] = {}
            for key, value in self.documents.items():
                if value.profile == profile and value.collection == collection:
                    matches = all(value.metadata.get(k) == v for k, v in filters.items())
                    if matches:
                        continue
                keep[key] = value
            self.documents = keep
        return deleted

    def retention_run(self, profile: str, collection: str, older_than_days: int) -> int:
        """Execute retention run."""
        # Covers: FR-16
        threshold = datetime.now(timezone.utc) - timedelta(days=older_than_days)  # noqa: UP017
        deleted_count = 0
        for doc_id, value in list(self.documents.items()):
            if (
                value.profile == profile
                and value.collection == collection
                and value.created_at < threshold
                and self.delete_by_id(profile, collection, doc_id)
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
        return self.queue.get(job_id)

    def job_cancel(self, job_id: str) -> JobRecord:
        """Execute job cancel."""
        return self.queue.cancel(job_id)

    def job_retry(self, job_id: str) -> JobRecord:
        """Execute job retry."""
        job = self.queue.retry(job_id)
        if job.status is JobStatus.queued:
            try:
                return self.queue.run(job_id=job_id)
            except RuntimeError:
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
            healthy = bool(self._run_async(asyncio.wait_for(self._llm_client.health(), timeout=15.0)))
            dims = self._embedding_dimension() if healthy else 0
            return {
                "status": "ok" if healthy else "error",
                "provider": self._llm_provider,
                "model": self._llm_model,
                "dimensions": dims,
            }
        except Exception:
            return {"status": "error", "provider": self._llm_provider, "model": self._llm_model, "dimensions": 0}

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
            record_ids = asyncio.run(
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
            healthy, ir = asyncio.run(
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
            "ocr_applied": bool(meta.get("ocr_applied", False)),
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
        }

    def ingest_stream_open(self, profile: str, collection: str, ordering_key: str) -> str:
        """Execute ingest stream open."""
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
    value = get_config(path)
    if value is not None:
        return value
    # Try env-var-to-path conversion if the original key didn't match.
    converted = _env_key_to_config_path(path)
    if converted != path:
        value = get_config(converted)
        if value is not None:
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
    from cloud_dog_config import get_config  # type: ignore
    for key in keys:
        direct = str(os.environ.get(key, "")).strip()
        if direct:
            return direct
        # Try dotted config path first, then env-var-to-path conversion.
        for path in (key, _env_key_to_config_path(key)):
            try:
                value = str(get_config(path) or "").strip()
            except Exception:
                value = ""
            if value:
                return value
    raise RuntimeError(f"Missing required configuration: {', '.join(keys)}")


def _resolve_queue_database_url(audit_path: str) -> str:
    """Resolve the queue database URL, defaulting to a per-instance SQLite file."""
    for path in ("index.db.url", "db.url"):
        value = str(_cfg(path, "") or "").strip()
        if value:
            return value
    base_path = Path(audit_path).with_suffix(".queue.db")
    return f"sqlite+aiosqlite:///{base_path}"


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
