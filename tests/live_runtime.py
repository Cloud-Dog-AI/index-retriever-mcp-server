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
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from uuid import uuid4

from cloud_dog_config.vault.client import (  # type: ignore[import-untyped]
    VaultClient,
    VaultConnectionConfig,
)
from cloud_dog_jobs import JobQueue, JobRequest, SQLQueueBackend
from cloud_dog_llm import get_llm_client
from cloud_dog_vdb import CollectionSpec, Record, SearchRequest, get_vdb_client
from cloud_dog_vdb.capabilities.planner import plan_search as vdb_plan_search
from cloud_dog_vdb.domain.models import CapabilityDescriptor
from cloud_dog_vdb.ingestion import ParserIngestionOptions, build_parser_registry, ingest_document
from cloud_dog_vdb.ingestion.ocr.planner import decide_ocr

ROOT = Path(__file__).resolve().parents[1]
_SECRET_FIELD_PATTERN = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*([^\s,;]+)")


def _load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@lru_cache(maxsize=1)
def _load_local_env_defaults() -> None:
    """Populate process env from local env files without overriding existing os.environ values."""
    _load_env_file(ROOT / ".env")
    _load_env_file(ROOT / ".env.local")

    cwd = Path.cwd()
    if cwd != ROOT:
        _load_env_file(cwd / ".env")
        _load_env_file(cwd / ".env.local")


def _env(*keys: str, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key)
        if value is not None and value != "":
            return value
    return default


def _infer_filename(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    candidate = parsed.path if parsed.scheme else source_uri
    return Path(unquote(candidate)).name or source_uri


def _infer_mime_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "text/plain"


def _redact_diagnostic_detail(detail: str) -> str:
    return _SECRET_FIELD_PATTERN.sub(r"\1=[REDACTED]", detail)


def _dataclass_to_dict(value: Any) -> dict[str, Any]:
    names = getattr(type(value), "__dataclass_fields__", {})
    return {name: getattr(value, name) for name in names}


def _as_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _extract_dev_section(payload: dict[str, Any]) -> dict[str, Any]:
    # VaultClient.read() already unwraps KV v2 data.data; try unwrapped first.
    if isinstance(payload.get("dev"), dict):
        return payload["dev"]
    if isinstance(payload.get("json"), dict) and isinstance(payload["json"].get("dev"), dict):
        return payload["json"]["dev"]
    if isinstance(payload.get("content"), str):
        parsed = json.loads(payload["content"])
        if isinstance(parsed.get("dev"), dict):
            return parsed["dev"]
    # Fallback: raw hvac response that still has data.data wrapper.
    raw = payload.get("data", {})
    if isinstance(raw, dict):
        inner = raw.get("data", {})
        if isinstance(inner, dict) and isinstance(inner.get("dev"), dict):
            return inner["dev"]
    raise RuntimeError("Vault config did not contain a dev section")


@lru_cache(maxsize=2)
def load_vault_dev_config(required: bool = True) -> dict[str, Any]:
    """
    Resolve dev config from live Vault using environment credentials.

    Vault is optional when required=False.
    """
    _load_local_env_defaults()

    vault_addr = _env("VAULT_ADDR", "CLOUD_DOG__VAULT__ADDR")
    vault_token = _env("VAULT_TOKEN", "CLOUD_DOG__VAULT__TOKEN")
    mount = _env("VAULT_MOUNT_POINT", "CLOUD_DOG__VAULT__MOUNT_POINT", default="cloud_dog_ai")
    config_path = _env("VAULT_CONFIG_PATH", "CLOUD_DOG__VAULT__CONFIG_PATH", default="config")

    if not vault_addr or not vault_token:
        if required:
            raise RuntimeError("Vault credentials are missing in environment")
        return {}

    try:
        client = VaultClient(
            VaultConnectionConfig(
                server=vault_addr.rstrip("/"),
                token=vault_token,
                timeout_seconds=15.0,
                mount_point=mount.strip("/"),
            )
        )
        # _split_mount expects path to include mount prefix as first segment;
        # pass mount/config_path so it splits correctly to (mount, config_path).
        read_path = f"{mount.strip('/')}/{config_path.lstrip('/') or 'config'}"
        payload = client.read(read_path)
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise RuntimeError("Vault payload is not a mapping")
        return _extract_dev_section(payload)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, RuntimeError):
        if required:
            raise
        return {}


def _nested_dict(root: dict[str, Any], *keys: str) -> dict[str, Any]:
    cur: Any = root
    for key in keys:
        if not isinstance(cur, dict):
            return {}
        cur = cur.get(key)
    return cur if isinstance(cur, dict) else {}


def _qdrant_url_from_env() -> str:
    explicit = _env("CLOUD_DOG__INDEX__VDB__QDRANT_URL", "QDRANT_URL")
    if explicit:
        return explicit
    host = _env("CLOUD_DOG__INDEX__VDB__HOST", "QDRANT_HOST")
    if not host:
        return ""
    port = _env("CLOUD_DOG__INDEX__VDB__PORT", "QDRANT_PORT", default="6333")
    scheme = _env("CLOUD_DOG__INDEX__VDB__QDRANT_SCHEME", "QDRANT_SCHEME", default="http")
    return f"{scheme}://{host}:{port}"


def _qdrant_url_from_vault(raw: dict[str, Any]) -> str:
    explicit = str(raw.get("url", ""))
    if explicit:
        return explicit
    host = str(raw.get("host", ""))
    if not host:
        return ""
    port = str(raw.get("port", "6333") or "6333")
    scheme = str(raw.get("scheme", "http") or "http")
    return f"{scheme}://{host}:{port}"


def _infinity_url_from_env() -> str:
    explicit = _env("CLOUD_DOG__INDEX__VDB__INFINITY_URL", "INFINITY_URL")
    if explicit:
        return explicit
    host = _env("CLOUD_DOG__INDEX__VDB__INFINITY_HOST", "INFINITY_HOST")
    if not host:
        return ""
    port = _env("CLOUD_DOG__INDEX__VDB__INFINITY_PORT", "INFINITY_PORT", default="8080")
    scheme = _env("CLOUD_DOG__INDEX__VDB__INFINITY_SCHEME", "INFINITY_SCHEME", default="http")
    return f"{scheme}://{host}:{port}"


def _infinity_url_from_vault(raw: dict[str, Any]) -> str:
    explicit = str(raw.get("base_url", raw.get("url", "")))
    if explicit:
        return explicit
    host = str(raw.get("host", ""))
    if not host:
        return ""
    port = str(raw.get("port", raw.get("client_port", "8080")) or "8080")
    return f"http://{host}:{port}"


def _opensearch_url_from_env() -> str:
    explicit = _env("CLOUD_DOG__INDEX__VDB__OPENSEARCH_URL", "OPENSEARCH_URL")
    if explicit:
        return explicit
    host = _env("CLOUD_DOG__INDEX__VDB__OPENSEARCH_HOST", "OPENSEARCH_HOST")
    if not host:
        return ""
    port = _env("CLOUD_DOG__INDEX__VDB__OPENSEARCH_PORT", "OPENSEARCH_PORT", default="9200")
    return f"http://{host}:{port}"


def _opensearch_url_from_vault(raw: dict[str, Any]) -> str:
    explicit = str(raw.get("base_url", raw.get("url", "")))
    if explicit:
        return explicit
    host = str(raw.get("host", ""))
    if not host:
        return ""
    port = str(raw.get("port", "9200") or "9200")
    return f"http://{host}:{port}"


def _weaviate_url_from_env() -> str:
    explicit = _env("CLOUD_DOG__INDEX__VDB__WEAVIATE_URL", "WEAVIATE_URL")
    if explicit:
        return explicit
    host = _env("CLOUD_DOG__INDEX__VDB__WEAVIATE_HOST", "WEAVIATE_HOST")
    if not host:
        return ""
    port = _env("CLOUD_DOG__INDEX__VDB__WEAVIATE_PORT", "WEAVIATE_PORT", default="8080")
    scheme = _env("CLOUD_DOG__INDEX__VDB__WEAVIATE_SCHEME", "WEAVIATE_SCHEME", default="http")
    return f"{scheme}://{host}:{port}"


def _weaviate_url_from_vault(raw: dict[str, Any]) -> str:
    explicit = str(raw.get("base_url", raw.get("url", "")))
    if explicit:
        return explicit
    host = str(raw.get("host", ""))
    if not host:
        return ""
    port = str(raw.get("port", "8080") or "8080")
    scheme = str(raw.get("scheme", "http") or "http")
    return f"{scheme}://{host}:{port}"


def _pgvector_uri_from_env() -> str:
    return _env("CLOUD_DOG__INDEX__VDB__PGVECTOR_DATABASE_URI", "PGVECTOR_DATABASE_URI")


def _pgvector_uri_from_vault(raw: dict[str, Any]) -> str:
    explicit = str(raw.get("database_uri", raw.get("url", "")))
    if explicit:
        return explicit
    username = str(raw.get("username", ""))
    password = str(raw.get("password", ""))
    host = str(raw.get("host", ""))
    port = str(raw.get("port", "5432") or "5432")
    database = str(raw.get("database", "postgres") or "postgres")
    if not username or not password or not host:
        return ""
    return f"postgresql://{username}:{password}@{host}:{port}/{database}"


def _postgres_url_from_vault(raw: dict[str, Any]) -> str:
    username = str(raw.get("username", ""))
    password = str(raw.get("password", ""))
    host = str(raw.get("host", ""))
    port = str(raw.get("port", "5432") or "5432")
    database = str(raw.get("database", "postgres") or "postgres")
    if not username or not password or not host:
        return ""
    return f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}"


def _normalise_queue_db_url(database_url: str) -> str:
    if database_url.startswith("sqlite+aiosqlite://"):
        return "sqlite://" + database_url[len("sqlite+aiosqlite://") :]
    if database_url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + database_url[len("postgresql+asyncpg://") :]
    return database_url


@dataclass(frozen=True, slots=True)
class LiveRuntimeConfig:
    embedding_base_url: str
    embedding_model: str
    embedding_api_key: str
    chroma_url: str
    chroma_auth_token: str
    qdrant_url: str
    qdrant_api_key: str
    opensearch_url: str
    opensearch_username: str
    opensearch_password: str
    pgvector_database_uri: str
    weaviate_url: str
    weaviate_api_key: str
    infinity_url: str
    infinity_api_key: str
    queue_db_url: str
    default_backend: str


@lru_cache(maxsize=1)
def resolve_live_runtime_config() -> LiveRuntimeConfig:
    _load_local_env_defaults()

    embedding_base_url = _env("CLOUD_DOG__INDEX__EMBEDDING__BASE_URL", "EMBED_BASE_URL")
    embedding_model = _env("CLOUD_DOG__INDEX__EMBEDDING__MODEL", default="nomic-embed-text")
    embedding_api_key = _env("CLOUD_DOG__INDEX__EMBEDDING__API_KEY", "EMBED_API_KEY")

    chroma_url = _env("CLOUD_DOG__INDEX__VDB__CHROMA_URL", "CHROMA_URL")
    chroma_auth_token = _env("CLOUD_DOG__INDEX__VDB__CHROMA_AUTH_TOKEN", "CHROMA_AUTH_TOKEN")

    qdrant_url = _qdrant_url_from_env()
    qdrant_api_key = _env("CLOUD_DOG__INDEX__VDB__QDRANT_API_KEY", "CLOUD_DOG__INDEX__VDB__API_KEY", "QDRANT_API_KEY")
    opensearch_url = _opensearch_url_from_env()
    opensearch_username = _env("CLOUD_DOG__INDEX__VDB__OPENSEARCH_USERNAME", "OPENSEARCH_USERNAME")
    opensearch_password = _env("CLOUD_DOG__INDEX__VDB__OPENSEARCH_PASSWORD", "OPENSEARCH_PASSWORD")
    pgvector_database_uri = _pgvector_uri_from_env()
    weaviate_url = _weaviate_url_from_env()
    weaviate_api_key = _env("CLOUD_DOG__INDEX__VDB__WEAVIATE_API_KEY", "WEAVIATE_API_KEY")
    infinity_url = _infinity_url_from_env()
    infinity_api_key = _env("CLOUD_DOG__INDEX__VDB__INFINITY_API_KEY", "INFINITY_API_KEY")

    queue_db_url = _env("INDEX_RETRIEVER_DB_URL", "CLOUD_DOG__INDEX__DB__URL", "DB_URL")
    default_backend = _env("CLOUD_DOG__INDEX__VDB__PROVIDER", default="chroma").strip().lower() or "chroma"

    if (
        not embedding_base_url
        or not chroma_url
        or not qdrant_url
        or not queue_db_url
        or (chroma_url and not chroma_auth_token)
        or (qdrant_url and not qdrant_api_key)
        or _as_bool(_env("INDEX_RETRIEVER_LIVE_USE_VAULT_FALLBACK"), default=False)
    ):
        vault = load_vault_dev_config(required=False)
        if vault:
            ollama = _nested_dict(vault, "models", "ollama_nomic_embed_text_llm1")
            chroma = _nested_dict(vault, "vdbs", "chroma")
            qdrant = _nested_dict(vault, "vdbs", "qdrant")
            opensearch = _nested_dict(vault, "vdbs", "opensearch")
            pgvector = _nested_dict(vault, "vdbs", "pgvector")
            weaviate = _nested_dict(vault, "vdbs", "weaviate")
            infinity = _nested_dict(vault, "vdbs", "infinity")
            postgres = _nested_dict(vault, "databases", "providers", "postgres")

            if not embedding_base_url:
                embedding_base_url = str(ollama.get("base_url", ""))
            if not embedding_model:
                embedding_model = str(ollama.get("model", "nomic-embed-text")) or "nomic-embed-text"
            if not embedding_api_key:
                embedding_api_key = str(ollama.get("api_key", ""))

            if not chroma_url:
                chroma_url = str(chroma.get("base_url", ""))
            if not chroma_auth_token:
                chroma_auth_token = str(chroma.get("auth_token", ""))

            if not qdrant_url:
                qdrant_url = _qdrant_url_from_vault(qdrant)
            if not qdrant_api_key:
                qdrant_api_key = str(qdrant.get("api_key", ""))

            if not opensearch_url:
                opensearch_url = _opensearch_url_from_vault(opensearch)
            if not opensearch_username:
                opensearch_username = str(opensearch.get("username", ""))
            if not opensearch_password:
                opensearch_password = str(opensearch.get("password", ""))

            if not pgvector_database_uri:
                pgvector_database_uri = _pgvector_uri_from_vault(pgvector)

            if not weaviate_url:
                weaviate_url = _weaviate_url_from_vault(weaviate)
            if not weaviate_api_key:
                weaviate_api_key = str(weaviate.get("api_key", ""))

            if not infinity_url:
                infinity_url = _infinity_url_from_vault(infinity)
            if not infinity_api_key:
                infinity_api_key = str(infinity.get("api_key", ""))

            if not queue_db_url:
                queue_db_url = _postgres_url_from_vault(postgres)

    if not queue_db_url:
        queue_db_url = "sqlite:///data/index-retriever-live.db"
    queue_db_url = _normalise_queue_db_url(queue_db_url)

    enabled_backends = [
        backend
        for backend, present in (
            ("chroma", bool(chroma_url)),
            ("qdrant", bool(qdrant_url)),
            ("opensearch", bool(opensearch_url)),
            ("pgvector", bool(pgvector_database_uri)),
            ("weaviate", bool(weaviate_url)),
            ("infinity", bool(infinity_url)),
        )
        if present
    ]
    if default_backend not in enabled_backends and enabled_backends:
        default_backend = enabled_backends[0]

    if not embedding_base_url:
        raise RuntimeError(
            "Missing embedding endpoint. Set CLOUD_DOG__INDEX__EMBEDDING__BASE_URL/EMBED_BASE_URL "
            "or provide Vault env for fallback."
        )
    if not enabled_backends:
        raise RuntimeError(
            "Missing VDB endpoints. Set CLOUD_DOG__INDEX__VDB__CHROMA_URL and/or "
            "CLOUD_DOG__INDEX__VDB__QDRANT_URL and/or CLOUD_DOG__INDEX__VDB__OPENSEARCH_URL and/or "
            "CLOUD_DOG__INDEX__VDB__PGVECTOR_DATABASE_URI and/or CLOUD_DOG__INDEX__VDB__WEAVIATE_URL and/or "
            "CLOUD_DOG__INDEX__VDB__INFINITY_URL "
            "(or HOST/PORT), or provide Vault env for fallback."
        )

    return LiveRuntimeConfig(
        embedding_base_url=embedding_base_url,
        embedding_model=embedding_model or "nomic-embed-text",
        embedding_api_key=embedding_api_key,
        chroma_url=chroma_url,
        chroma_auth_token=chroma_auth_token,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        opensearch_url=opensearch_url,
        opensearch_username=opensearch_username,
        opensearch_password=opensearch_password,
        pgvector_database_uri=pgvector_database_uri,
        weaviate_url=weaviate_url,
        weaviate_api_key=weaviate_api_key,
        infinity_url=infinity_url,
        infinity_api_key=infinity_api_key,
        queue_db_url=queue_db_url,
        default_backend=default_backend,
    )


@dataclass(slots=True)
class LiveRecord:
    job_id: str
    record_id: str
    provider_id: str
    collection_name: str


@dataclass(frozen=True, slots=True)
class SourceIngestState:
    record: LiveRecord
    payload_signature: str
    indexed_at: datetime


@dataclass(frozen=True, slots=True)
class RuntimeDiagnosticError(ValueError):
    operation: str
    provider: str
    message: str
    detail: str

    def __str__(self) -> str:
        payload = {
            "error": {
                "code": "PROVIDER_DIAGNOSTIC",
                "operation": self.operation,
                "provider": self.provider,
                "message": self.message,
                "detail": _redact_diagnostic_detail(self.detail),
            }
        }
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)


class _PreviewVdbBridge:
    def __init__(self) -> None:
        self.records: list[Record] = []

    async def upsert_records(self, collection: str, records: list[Record], provider_id: str | None = None) -> list[str]:
        _ = collection, provider_id
        self.records.extend(records)
        return [str(record.record_id) for record in records]


class LiveIndexRuntime:
    """Live runtime for ST/IT/AT/QT using platform adapters and real services."""

    _run_prefix: str | None = None

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        if LiveIndexRuntime._run_prefix is None:
            configured = os.environ.get("INDEX_RETRIEVER_TEST_RUN_PREFIX", "").strip().lower()
            token = configured or uuid4().hex[:8]
            if not token[:1].isalpha():
                token = f"r{token}"
            LiveIndexRuntime._run_prefix = token
            os.environ["INDEX_RETRIEVER_TEST_RUN_PREFIX"] = LiveIndexRuntime._run_prefix
        self._namespace = f"{LiveIndexRuntime._run_prefix}_{uuid4().hex[:4]}"
        self._config = resolve_live_runtime_config()

        self.embedding_model = self._config.embedding_model
        self.embedding_provider = "ollama"
        self._embedding_dim: int | None = None

        self.llm_client = get_llm_client(
            {
                "llm": {"default_provider": "ollama"},
                "providers": {
                    "ollama": {
                        "enabled": True,
                        "base_url": self._config.embedding_base_url,
                        "model": self.embedding_model,
                        "api_key": self._config.embedding_api_key,
                        "timeout_seconds": 300,
                    }
                },
            }
        )

        vector_stores: dict[str, Any] = {"default_backend": self._config.default_backend}
        self._enabled_providers: set[str] = set()

        if self._config.chroma_url:
            self._enabled_providers.add("chroma")
            vector_stores["chroma"] = {
                "enabled": True,
                "base_url": self._config.chroma_url,
                "auth_token": self._config.chroma_auth_token,
                "timeout_seconds": 120,
                "local_mode": False,
            }

        if self._config.qdrant_url:
            self._enabled_providers.add("qdrant")
            vector_stores["qdrant"] = {
                "enabled": True,
                "base_url": self._config.qdrant_url,
                "api_key": self._config.qdrant_api_key,
                "timeout_seconds": 120,
                "local_mode": False,
            }

        if self._config.opensearch_url:
            self._enabled_providers.add("opensearch")
            vector_stores["opensearch"] = {
                "enabled": True,
                "base_url": self._config.opensearch_url,
                "username": self._config.opensearch_username,
                "password": self._config.opensearch_password,
                "timeout_seconds": 120,
                "local_mode": False,
            }

        if self._config.pgvector_database_uri:
            self._enabled_providers.add("pgvector")
            vector_stores["pgvector"] = {
                "enabled": True,
                "database_uri": self._config.pgvector_database_uri,
                "timeout_seconds": 120,
                "local_mode": False,
            }

        if self._config.weaviate_url:
            self._enabled_providers.add("weaviate")
            vector_stores["weaviate"] = {
                "enabled": True,
                "base_url": self._config.weaviate_url,
                "api_key": self._config.weaviate_api_key,
                "timeout_seconds": 120,
                "local_mode": False,
            }

        if self._config.infinity_url:
            self._enabled_providers.add("infinity")
            vector_stores["infinity"] = {
                "enabled": True,
                "base_url": self._config.infinity_url,
                "api_key": self._config.infinity_api_key,
                "database": _env("CLOUD_DOG__INDEX__VDB__INFINITY_DATABASE", default="default_db"),
                "timeout_seconds": 120,
                "local_mode": False,
            }

        self.vdb_client = get_vdb_client({"vector_stores": vector_stores})
        self.job_queue = JobQueue(SQLQueueBackend(self._config.queue_db_url))

        self._collections: set[tuple[str, str]] = set()
        self._stream_sessions: dict[str, dict[str, Any]] = {}
        self._profiles: dict[str, dict[str, Any]] = {
            "default": {"enabled": True, "backend": self._config.default_backend}
        }
        self._idempotency_records: dict[tuple[str, str, str], LiveRecord] = {}
        self._source_records: dict[tuple[str, str, str, str], SourceIngestState] = {}

    @classmethod
    def run_prefix(cls) -> str:
        return cls._run_prefix or os.environ.get("INDEX_RETRIEVER_TEST_RUN_PREFIX", "").strip().lower()

    def _run(self, coro: Any) -> Any:
        return self._loop.run_until_complete(coro)

    def _embedding_dimension(self) -> int:
        if self._embedding_dim is not None:
            return self._embedding_dim
        try:
            vectors = self._run(
                asyncio.wait_for(
                    self.llm_client.embed(["dimension probe"], provider_id=self.embedding_provider, model=self.embedding_model),
                    timeout=30.0,
                )
            )
            self._embedding_dim = len(vectors[0]) if vectors else 768
        except (asyncio.TimeoutError, Exception):
            self._embedding_dim = 768
        return self._embedding_dim

    def _collection_name(self, profile: str, collection: str, provider_id: str | None = None) -> str:
        base_name = f"{self._namespace}_{profile}_{collection}".replace("-", "_")
        if str(provider_id or "").strip().lower() == "pgvector" and base_name[:1].isdigit():
            base_name = f"idx_{base_name}"
        if str(provider_id or "").strip().lower() != "infinity":
            return base_name
        digest = sha256(base_name.encode("utf-8")).hexdigest()[:18]
        return f"idxinf_{digest}"

    @staticmethod
    def _payload_signature(text: str, metadata: dict[str, Any], indexing_signature: str) -> str:
        payload = {"text": text, "metadata": metadata, "indexing_signature": indexing_signature}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return sha256(raw).hexdigest()

    @staticmethod
    def _is_stale(indexed_at: datetime, now: datetime, stale_after_days: int | None) -> bool:
        if stale_after_days is None:
            return False
        return (now - indexed_at).total_seconds() >= stale_after_days * 86400

    def _forget_record(self, record_id: str) -> None:
        for key, value in list(self._idempotency_records.items()):
            if value.record_id == record_id:
                del self._idempotency_records[key]
        for key, value in list(self._source_records.items()):
            if value.record.record_id == record_id:
                del self._source_records[key]

    def required_live_providers(self) -> list[str]:
        raw = os.getenv("INDEX_RETRIEVER_LIVE_REQUIRED_PROVIDERS", "chroma")
        providers = [part.strip().lower() for part in raw.split(",") if part.strip()]
        return providers or sorted(self._enabled_providers)

    def _list_collection_names(self, provider_id: str) -> list[str]:
        rows = self._run(self.vdb_client.list_collections(provider_id=provider_id))
        names: list[str] = []
        for row in rows:
            if isinstance(row, dict):
                name = str(row.get("name", "")).strip()
                if name:
                    names.append(name)
        return names

    def list_run_collections(self, provider_id: str) -> list[str]:
        prefix = self.run_prefix().strip()
        if not prefix:
            return []
        marker = f"{prefix}_"
        return [name for name in self._list_collection_names(provider_id) if name.startswith(marker)]

    def _provider_capabilities_descriptor(self, provider_id: str) -> CapabilityDescriptor:
        if provider_id not in self._enabled_providers:
            raise ValueError(f"Provider not configured: {provider_id}")
        registry = getattr(self.vdb_client, "_registry", None)
        if registry is None:
            raise RuntimeError("VDB client registry is unavailable")
        adapter = registry.get(provider_id)
        return adapter.capabilities()

    def backend_capabilities(self, provider_id: str) -> dict[str, Any]:
        return _dataclass_to_dict(self._provider_capabilities_descriptor(provider_id))

    def plan_search(
        self,
        *,
        provider_id: str,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
        capability_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        descriptor = self._provider_capabilities_descriptor(provider_id)
        if capability_override:
            payload = _dataclass_to_dict(descriptor)
            payload.update(capability_override)
            descriptor = CapabilityDescriptor(**payload)

        request = SearchRequest(
            query_text=query,
            top_k=max(1, int(top_k)),
            filters=filters or {},
            score_threshold=score_threshold,
        )
        plan = dict(vdb_plan_search(request, descriptor))
        if request.filters and not plan.get("filters"):
            raise ValueError("Backend capabilities do not support metadata filters")
        return plan

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
    ) -> dict[str, Any]:
        filename = _infer_filename(source_uri)
        mime_type = _infer_mime_type(filename)
        opts = ParserIngestionOptions(
            parser_chain=list(parser_chain or ["internal"]),
            parser_options=parser_options or {},
            ocr_mode=ocr_mode,
            ocr_provider=ocr_provider,
            table_policy=table_policy,
            table_json_shape=table_json_shape,
        )
        base_metadata = dict(metadata or {})
        base_metadata.setdefault("tenant_id", "default")
        base_metadata.setdefault("source_uri", source_uri)
        base_metadata.setdefault("filename", filename)
        base_metadata.setdefault("mime_type", mime_type)
        bridge = _PreviewVdbBridge()
        checkpoints: list[dict[str, Any]] = []
        try:
            record_ids = self._run(
                ingest_document(
                    bridge,
                    "__preview__",
                    source,
                    source_uri=source_uri,
                    options=opts,
                    metadata=base_metadata,
                    parser_services=parser_services,
                    on_checkpoint=lambda stage, count: checkpoints.append({"stage": stage, "count": int(count)}),
                )
            )
        except Exception as exc:
            raise RuntimeDiagnosticError(
                operation="ingest_preview",
                provider=",".join(opts.parser_chain),
                message="Provider parsing/ingestion failed",
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc
        chunks = [str(record.content) for record in bridge.records]
        first_metadata = dict(bridge.records[0].metadata) if bridge.records else base_metadata
        return {
            "record_ids": [str(item) for item in record_ids],
            "chunks": chunks,
            "metadata": first_metadata,
            "checkpoints": checkpoints,
        }

    def parsers_list(self, parser_services: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        registry = build_parser_registry(parser_services)
        out: list[dict[str, Any]] = []
        for provider_id in registry.list_ids():
            provider = registry.get(provider_id)
            if provider is None:
                continue
            out.append(
                {
                    "provider_id": provider.provider_id,
                    "provider_version": provider.provider_version,
                    "capabilities": _dataclass_to_dict(provider.capabilities),
                }
            )
        return out

    def parser_test(
        self,
        *,
        provider_id: str,
        sample_text: str = "parser health check",
        source_uri: str = "inline://parser-test.txt",
        parser_services: dict[str, dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        registry = build_parser_registry(parser_services)
        provider = registry.get(provider_id)
        if provider is None:
            raise ValueError(f"Unknown parser provider: {provider_id}")
        filename = _infer_filename(source_uri)
        mime_type = _infer_mime_type(filename)

        async def _probe() -> tuple[bool, Any]:
            healthy = await provider.health_check()
            ir = await provider.parse_bytes(
                sample_text.encode("utf-8"),
                filename=filename,
                source_uri=source_uri,
                mime_type=mime_type,
                options=options or {},
            )
            return bool(healthy), ir

        try:
            healthy, ir = self._run(_probe())
        except Exception as exc:
            raise RuntimeDiagnosticError(
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
        result = self._run_pipeline_preview(
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
        meta = dict(result["metadata"])
        return {
            "source_uri": meta.get("source_uri", source_uri),
            "filename": meta.get("filename", _infer_filename(source_uri)),
            "mime_type": meta.get("mime_type", _infer_mime_type(_infer_filename(source_uri))),
            "chunk_count": len(result["chunks"]),
            "parser_provider": meta.get("parser_provider", ""),
            "parser_version": meta.get("parser_version", ""),
            "ocr_mode": meta.get("ocr_mode", ocr_mode),
            "ocr_applied": bool(meta.get("ocr_applied", False)),
            "table_policy": meta.get("table_policy", table_policy),
            "checkpoints": list(result["checkpoints"]),
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
        result = self._run_pipeline_preview(
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
        meta = dict(result["metadata"])
        return {
            "source_uri": source_uri,
            "text": "\n\n".join(chunk for chunk in result["chunks"] if chunk.strip()),
            "chunk_count": len(result["chunks"]),
            "parser_provider": meta.get("parser_provider", ""),
            "ocr_applied": bool(meta.get("ocr_applied", False)),
            "table_policy": meta.get("table_policy", table_policy),
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
        result = self._run_pipeline_preview(
            source=text.encode("utf-8"),
            source_uri=source_uri,
            parser_chain=parser_chain,
            parser_options=parser_options,
            parser_services=parser_services,
            table_policy=table_policy,
            table_json_shape=table_json_shape,
        )
        meta = dict(result["metadata"])
        table_like = [
            chunk
            for chunk in result["chunks"]
            if "|" in chunk or "<table" in chunk.lower() or ("{" in chunk and "}" in chunk)
        ]
        if not table_like and result["chunks"]:
            table_like = [str(result["chunks"][0])]
        return {
            "source_uri": source_uri,
            "table_policy": table_policy,
            "table_json_shape": table_json_shape,
            "table_count": len(table_like),
            "tables": table_like,
            "parser_provider": meta.get("parser_provider", ""),
        }

    def _resolve_provider_id(self, provider_id: str | None) -> str:
        candidate = (provider_id or "").strip().lower()
        if candidate:
            return candidate
        return self._config.default_backend

    def ensure_collection(self, profile: str, collection: str, provider_id: str | None = None) -> str:
        resolved_provider = self._resolve_provider_id(provider_id)
        name = self._collection_name(profile, collection, resolved_provider)
        if (resolved_provider, name) in self._collections:
            return name

        self._run(
            self.vdb_client.create_collection(
                CollectionSpec(
                    name=name,
                    embedding_dim=self._embedding_dimension(),
                    metadata={"embedding_model": self.embedding_model},
                ),
                provider_id=resolved_provider,
            )
        )
        self._collections.add((resolved_provider, name))
        return name

    def ingest_text(
        self,
        profile: str,
        collection: str,
        text: str,
        source: str,
        actor: str,
        provider_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        created_at: datetime | None = None,
        dedupe_policy: str = "skip",
        stale_after_days: int | None = None,
        indexing_signature: str | None = None,
    ) -> LiveRecord:
        if dedupe_policy not in {"skip", "replace", "version"}:
            raise ValueError(f"Unsupported dedupe policy: {dedupe_policy}")

        resolved_provider = self._resolve_provider_id(provider_id)
        now = created_at or datetime.now(timezone.utc)  # noqa: UP017
        collection_name = self.ensure_collection(profile, collection, provider_id=resolved_provider)
        effective_signature = (indexing_signature or self.embedding_model).strip() or self.embedding_model
        user_metadata = dict(metadata or {})
        payload_signature = self._payload_signature(text, user_metadata, effective_signature)
        idempotency_map_key = (resolved_provider, collection_name, idempotency_key or "")
        source_map_key = (resolved_provider, collection_name, source, effective_signature)

        if idempotency_key and dedupe_policy == "skip":
            existing = self._idempotency_records.get(idempotency_map_key)
            if existing is not None:
                return existing

        existing_source = self._source_records.get(source_map_key)
        if existing_source is not None:
            payload_changed = existing_source.payload_signature != payload_signature
            stale = self._is_stale(existing_source.indexed_at, now, stale_after_days)
            if dedupe_policy == "skip" and not payload_changed and not stale:
                return existing_source.record
            if dedupe_policy in {"skip", "replace"} and (payload_changed or stale):
                _ = self.delete_by_id(
                    profile,
                    collection,
                    existing_source.record.record_id,
                    provider_id=resolved_provider,
                )

        collection_name = self.ensure_collection(profile, collection, provider_id=resolved_provider)
        _ = self._run(self.llm_client.embed([text], provider_id=self.embedding_provider, model=self.embedding_model))

        request = JobRequest(
            job_type="ingest_text",
            queue_name="index-retriever",
            payload={"profile": profile, "collection": collection_name, "source": source},
            user_id=actor,
            idempotency_key=idempotency_key,
        )
        job_id = self.job_queue.submit(request)

        filename = _infer_filename(source)
        mime_type = _infer_mime_type(filename)
        base_metadata: dict[str, Any] = {
            "tenant_id": profile,
            "source": source,
            "source_uri": source,
            "source_type": "file" if "://" in source else "other",
            "filename": filename,
            "mime_type": mime_type,
            "lifecycle_state": "active",
            "created_at": now.isoformat().replace("+00:00", "Z"),
            "actor": actor,
            "profile": profile,
            "collection": collection,
            "indexing_signature": effective_signature,
        }
        if user_metadata:
            base_metadata.update(user_metadata)

        record_id = str(uuid4())
        self._run(
            self.vdb_client.upsert_records(
                collection_name,
                [Record(record_id=record_id, content=text, metadata=base_metadata)],
                provider_id=resolved_provider,
            )
        )
        record = LiveRecord(
            job_id=job_id, record_id=record_id, provider_id=resolved_provider, collection_name=collection_name
        )
        if idempotency_key:
            self._idempotency_records[idempotency_map_key] = record
        self._source_records[source_map_key] = SourceIngestState(
            record=record,
            payload_signature=payload_signature,
            indexed_at=now,
        )
        return record

    def ingest_reference(
        self,
        profile: str,
        collection: str,
        path: str,
        actor: str,
        provider_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        dedupe_policy: str = "skip",
        stale_after_days: int | None = None,
        indexing_signature: str | None = None,
    ) -> LiveRecord:
        with open(path, "rb") as handle:
            payload = handle.read()
        return self.ingest_text(
            profile=profile,
            collection=collection,
            text=payload.decode("utf-8", errors="replace"),
            source=f"file://{path}",
            actor=actor,
            provider_id=self._resolve_provider_id(provider_id),
            metadata=metadata,
            idempotency_key=idempotency_key,
            dedupe_policy=dedupe_policy,
            stale_after_days=stale_after_days,
            indexing_signature=indexing_signature,
        )

    def search(
        self,
        profile: str,
        collection: str,
        query: str,
        provider_id: str | None = None,
        filters: dict[str, Any] | None = None,
        top_k: int = 10,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        resolved_provider = self._resolve_provider_id(provider_id)
        collection_name = self._collection_name(profile, collection, resolved_provider)
        plan = self.plan_search(
            provider_id=resolved_provider,
            query=query,
            top_k=top_k,
            filters=filters,
            score_threshold=score_threshold,
        )
        response = self._run(
            self.vdb_client.search(
                collection_name,
                SearchRequest(
                    query_text=query,
                    top_k=int(plan.get("top_k", top_k)),
                    filters=dict(plan.get("filters", filters or {})),
                    score_threshold=score_threshold,
                ),
                provider_id=resolved_provider,
            )
        )
        out: list[dict[str, Any]] = []
        for item in response.results:
            payload = dict(item.payload)
            out.append(
                {
                    "id": item.id,
                    "score": item.score,
                    "content": payload.get("content", ""),
                    "metadata": payload.get("metadata", {}),
                }
            )
        return out

    def retrieve(self, profile: str, collection: str, record_id: str, provider_id: str | None = None) -> Record | None:
        resolved_provider = self._resolve_provider_id(provider_id)
        collection_name = self._collection_name(profile, collection, resolved_provider)
        return self._run(self.vdb_client.get_record(collection_name, record_id, provider_id=resolved_provider))

    def delete_by_id(self, profile: str, collection: str, record_id: str, provider_id: str | None = None) -> bool:
        resolved_provider = self._resolve_provider_id(provider_id)
        collection_name = self._collection_name(profile, collection, resolved_provider)
        deleted = bool(
            self._run(self.vdb_client.delete_record(collection_name, record_id, provider_id=resolved_provider))
        )
        if deleted:
            self._forget_record(record_id)
        return deleted

    def delete_by_filter(
        self,
        profile: str,
        collection: str,
        filters: dict[str, Any],
        provider_id: str | None = None,
    ) -> int:
        resolved_provider = self._resolve_provider_id(provider_id)
        collection_name = self._collection_name(profile, collection, resolved_provider)
        existing = self._run(self.vdb_client.list_records(collection_name, provider_id=resolved_provider))
        deleted = int(
            self._run(self.vdb_client.delete_by_filter(collection_name, filters, provider_id=resolved_provider))
        )
        if deleted:
            for record in existing:
                if all(record.metadata.get(key) == value for key, value in filters.items()):
                    self._forget_record(str(record.record_id))
        return deleted

    def retention_run(self, profile: str, collection: str, older_than_days: int, provider_id: str | None = None) -> int:
        resolved_provider = self._resolve_provider_id(provider_id)
        collection_name = self._collection_name(profile, collection, resolved_provider)
        records = self._run(self.vdb_client.list_records(collection_name, provider_id=resolved_provider))
        threshold = datetime.now(timezone.utc).timestamp() - (older_than_days * 86400)  # noqa: UP017
        deleted = 0
        for item in records:
            created_at = str(item.metadata.get("created_at", ""))
            try:
                ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
            except ValueError:
                continue
            if ts < threshold and self.delete_by_id(
                profile,
                collection,
                item.record_id,
                provider_id=resolved_provider,
            ):
                deleted += 1
        return deleted

    def queue_status(self) -> dict[str, Any]:
        return self.job_queue.health()

    def queue_health_check(self) -> bool:
        with suppress(Exception):
            status = self.queue_status()
            if isinstance(status, dict) and "backend_healthy" in status:
                return bool(status["backend_healthy"])
            return True
        return False

    def job_get(self, job_id: str) -> Any:
        return self.job_queue.get(job_id)

    def job_list(self, limit: int = 50) -> list[Any]:
        return self.job_queue.list(limit=limit)

    def job_cancel(self, job_id: str) -> bool:
        return self.job_queue.cancel(job_id)

    def job_retry(self, job_id: str) -> bool:
        retry = getattr(self.job_queue, "retry", None)
        if callable(retry):
            return bool(retry(job_id))
        return False

    def backend_health_check(self, provider_id: str | None = None) -> bool:
        resolved_provider = self._resolve_provider_id(provider_id)
        if resolved_provider not in self._enabled_providers:
            return False
        return bool(self._run(self.vdb_client.health_check(provider_id=resolved_provider)))

    def embedding_health_check(self) -> bool:
        return bool(self._run(self.llm_client.health()))

    def backend_write_probe(self, provider_id: str) -> tuple[bool, str]:
        if provider_id not in self._enabled_providers:
            return False, "provider not configured"

        probe_collection = self._collection_name("preflight", f"{provider_id}_{uuid4().hex[:6]}", provider_id)
        probe_id = str(uuid4())
        probe_metadata: dict[str, Any] = {
            "tenant_id": "preflight",
            "source_uri": f"probe://{provider_id}",
            "source_type": "api",
            "lifecycle_state": "active",
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),  # noqa: UP017
            "actor": "preflight",
            "profile": "preflight",
            "collection": probe_collection,
        }
        try:
            self._run(
                self.vdb_client.create_collection(
                    CollectionSpec(
                        name=probe_collection,
                        embedding_dim=self._embedding_dimension(),
                        metadata={"embedding_model": self.embedding_model},
                    ),
                    provider_id=provider_id,
                )
            )
            self._run(
                self.vdb_client.upsert_records(
                    probe_collection,
                    [Record(record_id=probe_id, content="live runtime preflight probe", metadata=probe_metadata)],
                    provider_id=provider_id,
                )
            )
            return True, "ok"
        except Exception as exc:  # pragma: no cover - depends on live backends
            return False, f"{exc.__class__.__name__}: {exc}"
        finally:
            with suppress(Exception):
                self._run(self.vdb_client.delete_collection(probe_collection, provider_id=provider_id))

    def preflight(self, required_providers: list[str] | None = None) -> list[str]:
        issues: list[str] = []
        print(f"[live-runtime] embedding_base_url={self._config.embedding_base_url}")
        if self._config.chroma_url:
            print(f"[live-runtime] chroma_url={self._config.chroma_url}")
        if self._config.qdrant_url:
            print(f"[live-runtime] qdrant_url={self._config.qdrant_url}")
        if self._config.opensearch_url:
            print(f"[live-runtime] opensearch_url={self._config.opensearch_url}")
        if self._config.pgvector_database_uri:
            print("[live-runtime] pgvector_database_uri=[configured]")
        if self._config.weaviate_url:
            print(f"[live-runtime] weaviate_url={self._config.weaviate_url}")
        if self._config.infinity_url:
            print(f"[live-runtime] infinity_url={self._config.infinity_url}")

        if not self.embedding_health_check():
            issues.append("embedding provider health check failed")
        if not self.queue_health_check():
            issues.append("job queue health check failed")

        providers = required_providers or self.required_live_providers()
        for provider_id in providers:
            if provider_id not in self._enabled_providers:
                issues.append(f"{provider_id}: provider not configured")
                continue
            healthy = self.backend_health_check(provider_id=provider_id)
            print(f"[live-runtime] provider={provider_id} health={healthy}")
            if not healthy:
                issues.append(f"{provider_id}: health check failed")
                continue
            writable, detail = self.backend_write_probe(provider_id=provider_id)
            print(f"[live-runtime] provider={provider_id} write_probe={writable} detail={detail}")
            if not writable:
                issues.append(f"{provider_id}: write probe failed ({detail})")

        return issues

    def cleanup(self) -> None:
        marker = f"{self._namespace}_"
        for provider_id in sorted(self._enabled_providers):
            with suppress(Exception):
                for collection_name in self._list_collection_names(provider_id):
                    if collection_name.startswith(marker):
                        self._run(self.vdb_client.delete_collection(collection_name, provider_id=provider_id))
        for provider_id, collection_name in list(self._collections):
            with suppress(Exception):
                self._run(self.vdb_client.delete_collection(collection_name, provider_id=provider_id))
            self._collections.discard((provider_id, collection_name))
        with suppress(Exception):
            self._loop.close()

    def profiles_list(self) -> list[str]:
        return sorted(self._profiles.keys())

    def profile_get(self, profile: str) -> dict[str, Any]:
        return self._profiles[profile]

    def admin_profile_create(self, profile: str, roles: set[str]) -> None:
        if "admin" not in roles:
            raise PermissionError("Admin role required")
        self._profiles[profile] = {"enabled": True, "backend": self._config.default_backend}

    def admin_collection_create(self, profile: str, collection: str, roles: set[str]) -> None:
        if "admin" not in roles:
            raise PermissionError("Admin role required")
        _ = self.ensure_collection(profile, collection)

    def collections_list(self, profile: str) -> list[str]:
        prefix = f"{self._namespace}_{profile}_"
        names = self._list_collection_names(self._config.default_backend)
        out = [name.removeprefix(prefix) for name in names if name.startswith(prefix)]
        return sorted(out)

    def admin_collection_delete(self, profile: str, collection: str, roles: set[str]) -> None:
        if "admin" not in roles:
            raise PermissionError("Admin role required")
        collection_name = self._collection_name(profile, collection, self._config.default_backend)
        with suppress(Exception):
            self._run(self.vdb_client.delete_collection(collection_name, provider_id=self._config.default_backend))
        self._collections.discard((self._config.default_backend, collection_name))
        for key, value in list(self._source_records.items()):
            if value.record.collection_name == collection_name:
                del self._source_records[key]
        for key, value in list(self._idempotency_records.items()):
            if value.collection_name == collection_name:
                del self._idempotency_records[key]

    def ingest_stream_open(
        self,
        profile: str,
        collection: str,
        ordering_key: str,
        provider_id: str | None = None,
    ) -> str:
        resolved_provider = self._resolve_provider_id(provider_id)
        session_id = str(uuid4())
        self._stream_sessions[session_id] = {
            "profile": profile,
            "collection": collection,
            "ordering_key": ordering_key,
            "provider_id": resolved_provider,
            "job_ids": [],
        }
        return session_id

    def ingest_stream_event(
        self,
        session_id: str,
        text: str,
        actor: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        session = self._stream_sessions[session_id]
        rec = self.ingest_text(
            profile=str(session["profile"]),
            collection=str(session["collection"]),
            text=text,
            source=f"stream://{session['ordering_key']}",
            actor=actor,
            provider_id=str(session["provider_id"]),
            metadata=metadata,
        )
        session["job_ids"].append(rec.job_id)
        return rec.job_id

    def ingest_stream_close(self, session_id: str) -> dict[str, Any]:
        session = self._stream_sessions.pop(session_id)
        return {
            "session_id": session_id,
            "job_ids": list(session["job_ids"]),
            "ingested_events": len(session["job_ids"]),
            "ordering_key": session["ordering_key"],
        }
