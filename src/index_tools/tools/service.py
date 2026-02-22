# index-retriever-mcp-server — Index Service
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: In-memory end-to-end service orchestration for profiles, ingest, search, and jobs.

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
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

        self.vdb = InMemoryVdbAdapter()
        self.search_engine = SearchEngine(adapter=self.vdb)
        self.collection_manager = CollectionManager(adapter=self.vdb)
        self.queue = QueueEngine()
        self.audit_logger = AuditLogger(path=audit_path)
        self.embedding_adapter = EmbeddingAdapter(provider=resolved_provider, model=resolved_model)
        self.profiles: dict[str, dict[str, Any]] = {
            "default": {
                "enabled": True,
                "backend": resolved_backend,
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
        return self.search_engine.search(
            collection=self._collection_key(profile, collection),
            query=query,
            top_k=top_k,
            filters=filters,
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
        return self.vdb.health_check()

    def embedding_health_check(self) -> dict[str, str | int]:
        """Execute embedding health check."""
        vectors = self.embedding_adapter.embed(["health check"])
        dims = len(vectors[0]) if vectors else 0
        return {"status": "ok", "dimensions": dims}

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


def _required_env(*keys: str) -> str:
    """Read a required setting from environment using first non-empty key."""
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    raise RuntimeError(f"Missing required configuration: {', '.join(keys)}")
