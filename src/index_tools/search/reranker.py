# index-retriever-mcp-server — Search Reranker
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Optional result reranking helpers.

from __future__ import annotations


def _score(value: object) -> float:
    if isinstance(value, (int, float, str)):
        return float(value)
    return 0.0


def rerank_by_score(results: list[dict[str, object]]) -> list[dict[str, object]]:
    """Sort results by descending score if score key exists."""
    return sorted(results, key=lambda row: _score(row.get("score", 0.0)), reverse=True)
