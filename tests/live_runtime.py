# index-retriever-mcp-server — Live Test Runtime
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Env-first live runtime with optional Vault fallback for platform VDB/LLM/jobs.

from __future__ import annotations

import asyncio
import json
import os
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from cloud_dog_jobs import JobQueue, JobRequest, SQLQueueBackend
from cloud_dog_llm import get_llm_client
from cloud_dog_vdb import CollectionSpec, Record, SearchRequest, get_vdb_client

ROOT = Path(__file__).resolve().parents[1]


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


def _as_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _extract_dev_section(payload: dict[str, Any]) -> dict[str, Any]:
    root = payload["data"]["data"]
    if isinstance(root.get("dev"), dict):
        return root["dev"]
    if isinstance(root.get("json"), dict) and isinstance(root["json"].get("dev"), dict):
        return root["json"]["dev"]
    if isinstance(root.get("content"), str):
        parsed = json.loads(root["content"])
        if isinstance(parsed.get("dev"), dict):
            return parsed["dev"]
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

    url = f"{vault_addr.rstrip('/')}/v1/{mount}/data/{config_path.lstrip('/')}"
    req = Request(url, headers={"X-Vault-Token": vault_token}, method="GET")
    try:
        with urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
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

            if not queue_db_url:
                queue_db_url = _postgres_url_from_vault(postgres)

    if not queue_db_url:
        queue_db_url = "sqlite:///data/index-retriever-live.db"
    queue_db_url = _normalise_queue_db_url(queue_db_url)

    enabled_backends = [backend for backend, url in (("chroma", chroma_url), ("qdrant", qdrant_url)) if url]
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
            "CLOUD_DOG__INDEX__VDB__QDRANT_URL (or HOST/PORT), or provide Vault env for fallback."
        )

    return LiveRuntimeConfig(
        embedding_base_url=embedding_base_url,
        embedding_model=embedding_model or "nomic-embed-text",
        embedding_api_key=embedding_api_key,
        chroma_url=chroma_url,
        chroma_auth_token=chroma_auth_token,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
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


class LiveIndexRuntime:
    """Live runtime for ST/IT/AT/QT using platform adapters and real services."""

    _run_prefix: str | None = None

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        if LiveIndexRuntime._run_prefix is None:
            configured = os.environ.get("INDEX_RETRIEVER_TEST_RUN_PREFIX", "").strip().lower()
            LiveIndexRuntime._run_prefix = configured or uuid4().hex[:8]
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

        self.vdb_client = get_vdb_client({"vector_stores": vector_stores})
        self.job_queue = JobQueue(SQLQueueBackend(self._config.queue_db_url))

        self._collections: set[tuple[str, str]] = set()
        self._stream_sessions: dict[str, dict[str, Any]] = {}
        self._profiles: dict[str, dict[str, Any]] = {"default": {"enabled": True}}
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
        vectors = self._run(
            self.llm_client.embed(["dimension probe"], provider_id=self.embedding_provider, model=self.embedding_model)
        )
        self._embedding_dim = len(vectors[0]) if vectors else 768
        return self._embedding_dim

    def _collection_name(self, profile: str, collection: str) -> str:
        return f"{self._namespace}_{profile}_{collection}".replace("-", "_")

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

    def ensure_collection(self, profile: str, collection: str, provider_id: str = "chroma") -> str:
        name = self._collection_name(profile, collection)
        if (provider_id, name) in self._collections:
            return name

        self._run(
            self.vdb_client.create_collection(
                CollectionSpec(
                    name=name,
                    embedding_dim=self._embedding_dimension(),
                    metadata={"embedding_model": self.embedding_model},
                ),
                provider_id=provider_id,
            )
        )
        self._collections.add((provider_id, name))
        return name

    def ingest_text(
        self,
        profile: str,
        collection: str,
        text: str,
        source: str,
        actor: str,
        provider_id: str = "chroma",
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        created_at: datetime | None = None,
        dedupe_policy: str = "skip",
        stale_after_days: int | None = None,
        indexing_signature: str | None = None,
    ) -> LiveRecord:
        if dedupe_policy not in {"skip", "replace", "version"}:
            raise ValueError(f"Unsupported dedupe policy: {dedupe_policy}")

        now = created_at or datetime.now(timezone.utc)  # noqa: UP017
        collection_name = self.ensure_collection(profile, collection, provider_id=provider_id)
        effective_signature = (indexing_signature or self.embedding_model).strip() or self.embedding_model
        user_metadata = dict(metadata or {})
        payload_signature = self._payload_signature(text, user_metadata, effective_signature)
        idempotency_map_key = (provider_id, collection_name, idempotency_key or "")
        source_map_key = (provider_id, collection_name, source, effective_signature)

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
                _ = self.delete_by_id(profile, collection, existing_source.record.record_id, provider_id=provider_id)

        collection_name = self.ensure_collection(profile, collection, provider_id=provider_id)
        _ = self._run(self.llm_client.embed([text], provider_id=self.embedding_provider, model=self.embedding_model))

        request = JobRequest(
            job_type="ingest_text",
            queue_name="index-retriever",
            payload={"profile": profile, "collection": collection_name, "source": source},
            user_id=actor,
            idempotency_key=idempotency_key,
        )
        job_id = self.job_queue.submit(request)

        base_metadata: dict[str, Any] = {
            "tenant_id": profile,
            "source": source,
            "source_uri": source,
            "source_type": "file" if "://" in source else "other",
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
                provider_id=provider_id,
            )
        )
        record = LiveRecord(job_id=job_id, record_id=record_id, provider_id=provider_id, collection_name=collection_name)
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
        provider_id: str = "chroma",
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
            provider_id=provider_id,
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
        provider_id: str = "chroma",
        filters: dict[str, Any] | None = None,
        top_k: int = 10,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        collection_name = self._collection_name(profile, collection)
        response = self._run(
            self.vdb_client.search(
                collection_name,
                SearchRequest(
                    query_text=query,
                    top_k=top_k,
                    filters=filters or {},
                    score_threshold=score_threshold,
                ),
                provider_id=provider_id,
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

    def retrieve(self, profile: str, collection: str, record_id: str, provider_id: str = "chroma") -> Record | None:
        collection_name = self._collection_name(profile, collection)
        return self._run(self.vdb_client.get_record(collection_name, record_id, provider_id=provider_id))

    def delete_by_id(self, profile: str, collection: str, record_id: str, provider_id: str = "chroma") -> bool:
        collection_name = self._collection_name(profile, collection)
        deleted = bool(self._run(self.vdb_client.delete_record(collection_name, record_id, provider_id=provider_id)))
        if deleted:
            self._forget_record(record_id)
        return deleted

    def delete_by_filter(
        self,
        profile: str,
        collection: str,
        filters: dict[str, Any],
        provider_id: str = "chroma",
    ) -> int:
        collection_name = self._collection_name(profile, collection)
        existing = self._run(self.vdb_client.list_records(collection_name, provider_id=provider_id))
        deleted = int(self._run(self.vdb_client.delete_by_filter(collection_name, filters, provider_id=provider_id)))
        if deleted:
            for record in existing:
                if all(record.metadata.get(key) == value for key, value in filters.items()):
                    self._forget_record(str(record.record_id))
        return deleted

    def retention_run(self, profile: str, collection: str, older_than_days: int, provider_id: str = "chroma") -> int:
        collection_name = self._collection_name(profile, collection)
        records = self._run(self.vdb_client.list_records(collection_name, provider_id=provider_id))
        threshold = datetime.now(timezone.utc).timestamp() - (older_than_days * 86400)  # noqa: UP017
        deleted = 0
        for item in records:
            created_at = str(item.metadata.get("created_at", ""))
            try:
                ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
            except ValueError:
                continue
            if ts < threshold and self.delete_by_id(profile, collection, item.record_id, provider_id=provider_id):
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

    def backend_health_check(self, provider_id: str = "chroma") -> bool:
        if provider_id not in self._enabled_providers:
            return False
        return bool(self._run(self.vdb_client.health_check(provider_id=provider_id)))

    def embedding_health_check(self) -> bool:
        return bool(self._run(self.llm_client.health()))

    def backend_write_probe(self, provider_id: str) -> tuple[bool, str]:
        if provider_id not in self._enabled_providers:
            return False, "provider not configured"

        probe_collection = self._collection_name("preflight", f"{provider_id}_{uuid4().hex[:6]}")
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
        self._profiles[profile] = {"enabled": True}

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
        collection_name = self._collection_name(profile, collection)
        with suppress(Exception):
            self._run(self.vdb_client.delete_collection(collection_name, provider_id=self._config.default_backend))
        self._collections.discard((self._config.default_backend, collection_name))
        for key, value in list(self._source_records.items()):
            if value.record.collection_name == collection_name:
                del self._source_records[key]
        for key, value in list(self._idempotency_records.items()):
            if value.collection_name == collection_name:
                del self._idempotency_records[key]

    def ingest_stream_open(self, profile: str, collection: str, ordering_key: str, provider_id: str = "chroma") -> str:
        session_id = str(uuid4())
        self._stream_sessions[session_id] = {
            "profile": profile,
            "collection": collection,
            "ordering_key": ordering_key,
            "provider_id": provider_id,
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
