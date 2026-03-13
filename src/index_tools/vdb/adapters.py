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

# index-retriever-mcp-server — VDB Adapters
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Adapter layer delegating VDB operations to cloud_dog_vdb.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    import cloud_dog_vdb  # type: ignore
except ImportError:  # pragma: no cover
    cloud_dog_vdb = None


@dataclass(slots=True)
class StoredDocument:
    """StoredDocument definition."""

    chunks: list[str]
    vectors: list[list[float]]
    metadata: dict[str, Any] = field(default_factory=dict)


class InMemoryVdbAdapter:
    """Fallback adapter for unit testing without external VDB services."""

    def __init__(self) -> None:
        """Initialise the instance state."""
        self.collections: dict[str, dict[str, StoredDocument]] = {}
        self.collection_dimensions: dict[str, int] = {}

    def create_collection(self, name: str, embedding_dim: int | None = None) -> None:
        """Execute create collection."""
        self.collections.setdefault(name, {})
        if embedding_dim is not None:
            self.collection_dimensions[name] = int(embedding_dim)

    def list_collections(self) -> list[str]:
        """Execute list collections."""
        return sorted(self.collections.keys())

    def delete_collection(self, name: str) -> None:
        """Execute delete collection."""
        self.collections.pop(name, None)
        self.collection_dimensions.pop(name, None)

    def upsert(
        self,
        collection: str,
        doc_id: str,
        chunks: list[str],
        vectors: list[list[float]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Execute upsert."""
        self._validate_embedding_dimensions(collection=collection, vectors=vectors)
        self.collections.setdefault(collection, {})[doc_id] = StoredDocument(
            chunks=chunks,
            vectors=vectors,
            metadata=metadata or {},
        )

    def delete_by_doc_id(self, collection: str, doc_id: str) -> bool:
        """Execute delete by doc id."""
        docs = self.collections.get(collection, {})
        return docs.pop(doc_id, None) is not None

    def delete_by_filter(self, collection: str, filters: dict[str, Any]) -> int:
        """Execute delete by filter."""
        docs = self.collections.get(collection, {})
        to_delete = [doc_id for doc_id, payload in docs.items() if _matches_filters(payload.metadata, filters)]
        for doc_id in to_delete:
            docs.pop(doc_id, None)
        return len(to_delete)

    def query(
        self,
        collection: str,
        query_text: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Execute query."""
        docs = self.collections.get(collection, {})
        results: list[dict[str, Any]] = []
        for doc_id, payload in docs.items():
            if filters and not _matches_filters(payload.metadata, filters):
                continue
            for idx, chunk in enumerate(payload.chunks):
                score = _score_chunk(query_text, chunk)
                if score < score_threshold:
                    continue
                if query_text.lower() in chunk.lower() or score > 0.0:
                    results.append(
                        {
                            "doc_id": doc_id,
                            "chunk_id": f"{doc_id}:{idx}",
                            "text": chunk,
                            "score": score,
                            "metadata": payload.metadata,
                        }
                    )
        ordered = sorted(results, key=lambda item: float(item["score"]), reverse=True)
        return ordered[:top_k]

    def health_check(self) -> dict[str, str]:
        """Execute health check."""
        return {"status": "ok", "backend": "in-memory"}

    def _validate_embedding_dimensions(self, collection: str, vectors: list[list[float]]) -> None:
        """Validate embedding vector dimensions for cross-ingest consistency."""
        if not vectors:
            return
        dims = {len(item) for item in vectors}
        if len(dims) != 1:
            raise ValueError("Embedding vectors contain inconsistent dimensions in a single upsert request")
        actual = next(iter(dims))
        expected = self.collection_dimensions.get(collection)
        if expected is None:
            self.collection_dimensions[collection] = actual
            return
        if expected != actual:
            raise ValueError(f"Embedding dimension mismatch for collection '{collection}': expected {expected}, got {actual}")


def _score_chunk(query_text: str, chunk: str) -> float:
    """Internal helper to score chunk."""
    query = set(query_text.lower().split())
    target = set(chunk.lower().split())
    if not query or not target:
        return 0.0
    overlap = len(query.intersection(target))
    return overlap / len(query)


def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Internal helper to matches filters."""
    return all(metadata.get(key) == expected for key, expected in filters.items())
