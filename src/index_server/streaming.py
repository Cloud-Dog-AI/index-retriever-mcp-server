# index-retriever-mcp-server — Streaming Interface
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Streaming ingestion wrappers for SSE and WebSocket style flows.

from __future__ import annotations

from typing import Any

from index_tools.tools.service import IndexService


def ingest_stream_open(service: IndexService, profile: str, collection: str, ordering_key: str) -> dict[str, str]:
    session_id = service.ingest_stream_open(profile=profile, collection=collection, ordering_key=ordering_key)
    return {"session_id": session_id}


def ingest_stream_event(
    service: IndexService,
    session_id: str,
    text: str,
    actor: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    job_id = service.ingest_stream_event(session_id=session_id, text=text, actor=actor, metadata=metadata)
    return {"job_id": job_id}


def ingest_stream_close(service: IndexService, session_id: str) -> dict[str, Any]:
    return service.ingest_stream_close(session_id=session_id)
