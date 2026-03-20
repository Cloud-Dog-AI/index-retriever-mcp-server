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

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from index_tools.tools.service import IndexService


@dataclass(slots=True)
class LocalRecord:
    job_id: str
    record_id: str
    provider_id: str
    collection_name: str


class LocalIndexRuntime:
    """Local runtime facade matching the live runtime surface used by ST tests."""

    def __init__(self) -> None:
        # Consume ST/UT env variables so env files are active inputs rather than decoration.
        ingest_root = os.getenv("INGEST_ROOT", "data/index-retriever-st")
        chroma_path = os.getenv("CHROMA_PATH", f"{ingest_root}/chroma")
        _ = os.getenv("DB_URL", "sqlite+aiosqlite:///data/index-retriever-st.db")
        _ = os.getenv("EMBED_BASE_URL", "http://127.0.0.1:11434/v1")
        _ = os.getenv("EMBED_API_KEY", "dummy")

        self._providers = {"chroma", "qdrant"}
        self._namespace = uuid4().hex[:8]
        self._root = Path(ingest_root)
        self._chroma_path = Path(chroma_path)
        self._root.mkdir(parents=True, exist_ok=True)
        self._chroma_path.mkdir(parents=True, exist_ok=True)
        self._job_to_doc: dict[str, str] = {}
        self._service = IndexService(audit_path=str(self._root / f"audit-{self._namespace}.jsonl"))

    def _collection_name(self, profile: str, collection: str) -> str:
        return f"{self._namespace}_{profile}_{collection}".replace("-", "_")

    def ensure_collection(self, profile: str, collection: str, provider_id: str = "chroma") -> str:
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        self._service.admin_collection_create(profile, collection, roles={"admin"})
        return self._collection_name(profile, collection)

    def ingest_text(
        self,
        profile: str,
        collection: str,
        text: str,
        source: str,
        actor: str,
        provider_id: str = "chroma",
        metadata: dict[str, object] | None = None,
        idempotency_key: str | None = None,
        created_at: datetime | None = None,
    ) -> LocalRecord:
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        existing = set(self._service.documents.keys())
        job_id = self._service.ingest_text(
            profile=profile,
            collection=collection,
            text=text,
            source=source,
            actor=actor,
            idempotency_key=idempotency_key,
            metadata=metadata,
            created_at=created_at,
        )

        new_ids = set(self._service.documents.keys()) - existing
        record_id = next(iter(new_ids), self._job_to_doc.get(job_id, ""))
        if not record_id:
            for candidate_id, payload in self._service.documents.items():
                if payload.profile == profile and payload.collection == collection and payload.source == source:
                    record_id = candidate_id
        if record_id:
            self._job_to_doc[job_id] = record_id

        return LocalRecord(
            job_id=job_id,
            record_id=record_id,
            provider_id=provider_id,
            collection_name=self._collection_name(profile, collection),
        )

    def search(
        self,
        profile: str,
        collection: str,
        query: str,
        provider_id: str = "chroma",
        filters: dict[str, object] | None = None,
        top_k: int = 10,
        score_threshold: float | None = None,
    ) -> list[dict[str, object]]:
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        threshold = 0.0 if score_threshold is None else score_threshold
        return self._service.search(
            profile=profile,
            collection=collection,
            query=query,
            top_k=top_k,
            filters=filters,
            score_threshold=threshold,
        )

    def retrieve(
        self,
        profile: str,
        collection: str,
        record_id: str,
        provider_id: str = "chroma",
    ) -> SimpleNamespace | None:
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        if record_id not in self._service.documents:
            return None
        payload = self._service.retrieve(record_id)
        return SimpleNamespace(
            record_id=record_id,
            content=str(payload.get("text", "")),
            metadata=dict(payload.get("metadata", {})),
            profile=profile,
            collection=collection,
        )

    def delete_by_id(self, profile: str, collection: str, record_id: str, provider_id: str = "chroma") -> bool:
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        return self._service.delete_by_id(profile, collection, record_id)

    def delete_by_filter(
        self,
        profile: str,
        collection: str,
        filters: dict[str, object],
        provider_id: str = "chroma",
    ) -> int:
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        return self._service.delete_by_filter(profile, collection, filters)

    def retention_run(self, profile: str, collection: str, older_than_days: int, provider_id: str = "chroma") -> int:
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        return self._service.retention_run(profile, collection, older_than_days)

    def queue_status(self) -> bool:
        _ = self._service.queue_status()
        return True

    def job_get(self, job_id: str) -> object:
        return self._service.job_get(job_id)

    def backend_health_check(self, provider_id: str = "chroma") -> bool:
        if provider_id not in self._providers:
            return False
        return self._service.backend_health_check().get("status") == "ok"

    def embedding_health_check(self) -> bool:
        return self._service.embedding_health_check().get("status") == "ok"

    def preflight(self, required_providers: list[str] | None = None) -> list[str]:
        providers = required_providers or sorted(self._providers)
        issues: list[str] = []
        if not self.embedding_health_check():
            issues.append("embedding provider health check failed")
        for provider_id in providers:
            if not self.backend_health_check(provider_id=provider_id):
                issues.append(f"{provider_id}: health check failed")
        return issues

    def cleanup(self) -> None:
        self._job_to_doc.clear()
