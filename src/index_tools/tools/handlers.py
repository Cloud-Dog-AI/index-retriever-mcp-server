# index-retriever-mcp-server — Tool Handlers
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tool handler implementations wired to core services.

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from index_tools.tools.definitions import IngestOutput, SearchInput, SearchOutput, SearchResult


def handle_search(input_data: SearchInput, search_fn: Callable[..., list[dict[str, Any]]]) -> SearchOutput:
    rows = search_fn(
        collection=input_data.collection,
        query=input_data.query,
        top_k=input_data.top_k,
        filters=input_data.filters,
    )
    results = [SearchResult.model_validate(row) for row in rows]
    return SearchOutput(results=results)


def handle_ingest_text() -> IngestOutput:
    return IngestOutput(job_id=str(uuid.uuid4()), status="queued")
