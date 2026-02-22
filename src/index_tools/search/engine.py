# index-retriever-mcp-server — Search Engine
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Query normalisation and vector backend search orchestration.

from __future__ import annotations

from typing import Any

from index_tools.vdb.adapters import InMemoryVdbAdapter


def normalise_query(query: str) -> str:
    """Normalise user query for deterministic backend matching."""
    return " ".join(query.strip().split())


def validate_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    """Validate metadata filters contain simple scalar values."""
    if not filters:
        return {}
    for key, value in filters.items():
        if not isinstance(key, str):
            raise ValueError("Filter keys must be strings")
        if not isinstance(value, (str, int, float, bool)):
            raise ValueError("Filter values must be scalar")
    return filters


class SearchEngine:
    """Search facade over configured vector backend adapter."""

    def __init__(self, adapter: InMemoryVdbAdapter | None = None) -> None:
        """Initialise the instance state."""
        self.adapter = adapter or InMemoryVdbAdapter()

    def search(
        self,
        collection: str,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Execute search."""
        checked_filters = validate_filters(filters)
        normalised = normalise_query(query)
        return self.adapter.query(
            collection=collection,
            query_text=normalised,
            top_k=top_k,
            filters=checked_filters,
            score_threshold=score_threshold,
        )
