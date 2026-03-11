# index-retriever-mcp-server — Index Service
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: In-memory end-to-end service orchestration for profiles, ingest, search, and jobs.

from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from uuid import uuid4

from index_tools.audit.events import AdminAuditEvent, IngestAuditEvent
from index_tools.audit.logger import AuditLogger
from index_tools.collections.manager import CollectionManager
from index_tools.embeddings.adapter import EmbeddingAdapter
from index_tools.pipeline.chunking import token_chunks
from index_tools.pipeline.metadata import build_metadata
from index_tools.queue.engine import QueueEngine
from index_tools.queue.models import JobRecord, JobStatus
from index_tools.search.engine import SearchEngine
from index_tools.vdb.adapters import InMemoryVdbAdapter

try:
    from cloud_dog_vdb import ParserIngestionOptions, SearchRequest, ingest_document
    from cloud_dog_vdb.capabilities.planner import plan_search as vdb_plan_search
    from cloud_dog_vdb.domain.models import CapabilityDescriptor
    from cloud_dog_vdb.ingestion.ocr.planner import decide_ocr
    from cloud_dog_vdb.ingestion.pipeline import build_parser_registry
except ImportError:  # pragma: no cover
    ParserIngestionOptions = None  # type: ignore[assignment]
    SearchRequest = None  # type: ignore[assignment]
    CapabilityDescriptor = None  # type: ignore[assignment]
    vdb_plan_search = None
    ingest_document = None
    decide_ocr = None
    build_parser_registry = None


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


class IndexService:
    """Service facade providing deterministic behaviour for all tool flows."""

    def __init__(
        self,
        audit_path: str,
        *,
        embedding_provider: str | None = None,
        embedding_model: str | None = None,
        default_backend: str | None = None,
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
        self.vdb = InMemoryVdbAdapter()
        self.search_engine = SearchEngine(adapter=self.vdb)
        self.collection_manager = CollectionManager(adapter=self.vdb)
        self.queue = QueueEngine()
        self.audit_logger = AuditLogger(path=audit_path)
        self.embedding_adapter = EmbeddingAdapter(provider=resolved_provider, model=resolved_model)
        self.profiles: dict[str, dict[str, Any]] = {
            "default": {
                "enabled": True,
                "backend": self._default_backend,
                "roles": {"reader", "writer", "maintainer", "admin"},
            }
        }
        self.documents: dict[str, DocumentRecord] = {}
        self.idempotency: dict[str, str] = {}
        self.stream_sessions: dict[str, StreamSession] = {}

    @staticmethod
    def _collection_key(profile: str, collection: str) -> str:
        """Internal helper to collection key."""
        return f"{profile}:{collection}"

    def _require_admin(self, roles: set[str]) -> None:
        """Internal helper to require admin."""
        if "admin" not in roles:
            raise PermissionError("Admin role required")

    def profiles_list(self) -> list[str]:
        """Execute profiles list."""
        return sorted(self.profiles.keys())

    def profile_get(self, profile: str) -> dict[str, Any]:
        """Execute profile get."""
        return self.profiles[profile]

    def admin_profile_create(self, profile: str, roles: set[str]) -> None:
        """Execute admin profile create."""
        self._require_admin(roles)
        self.profiles[profile] = {
            "enabled": True,
            "backend": self.profiles["default"]["backend"],
            "roles": {"reader", "writer", "maintainer"},
        }
        self.audit_logger.write_event(
            AdminAuditEvent(
                actor="admin",
                operation="admin",
                profile=profile,
                params={"action": "create"},
            )
        )

    def admin_profile_delete(self, profile: str, roles: set[str]) -> None:
        """Execute admin profile delete."""
        self._require_admin(roles)
        if profile == "default":
            raise ValueError("Default profile cannot be deleted")
        self.profiles.pop(profile, None)

    def collections_list(self, profile: str) -> list[str]:
        """Execute collections list."""
        prefix = f"{profile}:"
        output: list[str] = []
        for name in self.collection_manager.list():
            if name.startswith(prefix):
                output.append(name.removeprefix(prefix))
        return sorted(output)

    def admin_collection_create(self, profile: str, collection: str, roles: set[str]) -> None:
        """Execute admin collection create."""
        self._require_admin(roles)
        self.collection_manager.create(self._collection_key(profile, collection))

    def admin_collection_delete(self, profile: str, collection: str, roles: set[str]) -> None:
        """Execute admin collection delete."""
        self._require_admin(roles)
        self.collection_manager.delete(self._collection_key(profile, collection))

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
        if profile not in self.profiles:
            raise ValueError(f"Unknown profile: {profile}")

        collection_key = self._collection_key(profile, collection)
        self.collection_manager.create(collection_key)

        source_key = source + ":" + sha256(text.encode()).hexdigest()
        computed_key = self.queue.generate_idempotency_key(profile, collection, source_key)
        request_key = idempotency_key or computed_key
        if request_key in self.idempotency:
            return self.idempotency[request_key]

        job_id = str(uuid4())
        job = JobRecord(
            job_id=job_id,
            profile=profile,
            collection=collection,
            job_type="ingest_text",
            idempotency_key=request_key,
        )
        self.queue.enqueue(job)

        def _handler(_: JobRecord) -> None:
            """Internal helper to handler."""
            doc_id = str(uuid4())
            chunks = token_chunks(text, chunk_size=64, chunk_overlap=8)
            if not chunks:
                chunks = [text]
            vectors = self.embedding_adapter.embed(chunks)
            document_metadata = build_metadata(
                source=source,
                content=text.encode(),
                profile=profile,
                collection=collection,
            )
            if metadata:
                document_metadata.update(metadata)
            document_metadata.setdefault("source_uri", source)
            document_metadata.setdefault("filename", _infer_filename(str(document_metadata["source_uri"])))
            document_metadata.setdefault("mime_type", _infer_mime_type(str(document_metadata["filename"])))
            if created_at is not None:
                document_metadata["created_at"] = created_at.isoformat()
            else:
                document_metadata["created_at"] = datetime.now(timezone.utc).isoformat()  # noqa: UP017

            self.vdb.upsert(
                collection=collection_key,
                doc_id=doc_id,
                chunks=chunks,
                vectors=vectors,
                metadata=document_metadata,
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

            self.audit_logger.write_event(
                IngestAuditEvent(
                    actor=actor,
                    profile=profile,
                    collection=collection,
                    job_id=job_id,
                    params={"source": source, "metadata": metadata or {}},
                    counts={"docs": 1, "chunks": len(chunks)},
                )
            )

        self.queue.run(job_id=job_id, handler=_handler)
        self.idempotency[request_key] = job_id
        return job_id

    def ingest_reference(self, profile: str, collection: str, path: str, actor: str) -> str:
        """Execute ingest reference."""
        with open(path, "rb") as handle:
            payload = handle.read()
        return self.ingest_text(
            profile=profile,
            collection=collection,
            text=payload.decode("utf-8", errors="replace"),
            source=path,
            actor=actor,
        )

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
        planned = self.search_plan(profile=profile, query=query, top_k=top_k, filters=filters)
        return self.search_engine.search(
            collection=self._collection_key(profile, collection),
            query=query,
            top_k=int(planned.get("top_k", top_k)),
            filters=planned.get("filters", filters),
            score_threshold=score_threshold,
        )

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
        deleted = self.vdb.delete_by_doc_id(self._collection_key(profile, collection), doc_id)
        self.documents.pop(doc_id, None)
        return deleted

    def delete_by_filter(self, profile: str, collection: str, filters: dict[str, Any]) -> int:
        """Execute delete by filter."""
        deleted = self.vdb.delete_by_filter(self._collection_key(profile, collection), filters)
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
        doc_count = len([d for d in self.documents.values() if d.profile == profile and d.collection == collection])
        return {"documents": doc_count}

    def job_list(self) -> list[JobRecord]:
        """Execute job list."""
        return self.queue.list_jobs()

    def job_get(self, job_id: str) -> JobRecord:
        """Execute job get."""
        return self.queue.get(job_id)

    def job_wait(self, job_id: str) -> JobRecord:
        """Execute job wait."""
        return self.queue.get(job_id)

    def job_cancel(self, job_id: str) -> JobRecord:
        """Execute job cancel."""
        job = self.queue.get(job_id)
        job.status = JobStatus.cancelled
        return job

    def job_retry(self, job_id: str) -> JobRecord:
        """Execute job retry."""
        job = self.queue.get(job_id)
        if job.status is JobStatus.failed:
            job.status = JobStatus.queued
        return job

    def queue_status(self) -> dict[str, int]:
        """Execute queue status."""
        jobs = self.queue.list_jobs()
        total = len(jobs)
        running = len([j for j in jobs if j.status is JobStatus.running])
        failed = len([j for j in jobs if j.status is JobStatus.failed])
        return {"total": total, "running": running, "failed": failed}

    def backend_health_check(self) -> dict[str, str]:
        """Execute backend health check."""
        health = dict(self.vdb.health_check())
        health.setdefault("provider", self._default_backend)
        return health

    def embedding_health_check(self) -> dict[str, str | int]:
        """Execute embedding health check."""
        vectors = self.embedding_adapter.embed(["health check"])
        dims = len(vectors[0]) if vectors else 0
        return {"status": "ok", "dimensions": dims}

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


def _required_env(*keys: str) -> str:
    """Read a required setting from environment using first non-empty key."""
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    raise RuntimeError(f"Missing required configuration: {', '.join(keys)}")
