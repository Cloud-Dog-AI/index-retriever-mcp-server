# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""A2A server entrypoint for the authenticated A2A surface."""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from index_server.runtime_config import resolve_server_binding

A2A_SKILLS: tuple[dict[str, str], ...] = (
    {"id": "index_list", "name": "Index List", "description": "List indexed collections for the selected profile"},
    {"id": "bulk_index", "name": "Bulk Index", "description": "Queue one or more text documents for asynchronous indexing"},
    {"id": "ingest_text", "name": "Ingest Text", "description": "Ingest text into a profiled collection with embedding and indexing"},
    {"id": "ingest_upload", "name": "Ingest Upload", "description": "Upload a file for chunking, embedding, and indexing"},
    {"id": "ingest_reference", "name": "Ingest Reference", "description": "Ingest content from a URI (HTTP, S3, FTP, filesystem, etc.)"},
    {"id": "search", "name": "Search", "description": "Vector similarity search across indexed collections"},
    {"id": "retrieve", "name": "Retrieve", "description": "Retrieve a specific document by ID"},
    {"id": "collection_create", "name": "Create Collection", "description": "Create a new indexed collection within a profile"},
    {"id": "collection_list", "name": "List Collections", "description": "List collections for a profile"},
    {"id": "profiles_list", "name": "List Profiles", "description": "List configured storage profiles"},
    {"id": "ingest_health", "name": "Ingest Health", "description": "Per-profile ingest pipeline health status"},
    {"id": "backend_health_check", "name": "Backend Health", "description": "Vector database backend health check"},
    {"id": "file_upload", "name": "File Upload", "description": "Upload a file to service storage (PS-78)"},
    {"id": "file_list", "name": "File List", "description": "List stored service files (PS-78)"},
    {"id": "file_get", "name": "File Metadata", "description": "Get stored service file metadata (PS-78)"},
    {"id": "file_download", "name": "File Download", "description": "Download stored service file content (PS-78)"},
    {"id": "file_delete", "name": "File Delete", "description": "Delete a stored service file (PS-78)"},
    {"id": "source_config_create", "name": "Create Source Config", "description": "Create a connector source configuration"},
    {"id": "source_config_list", "name": "List Source Configs", "description": "List connector source configurations"},
    {"id": "source_config_get", "name": "Get Source Config", "description": "Read a connector source configuration"},
    {"id": "source_config_update", "name": "Update Source Config", "description": "Update a connector source configuration"},
    {"id": "source_config_delete", "name": "Delete Source Config", "description": "Delete a connector source configuration"},
    {"id": "hdro_extract", "name": "UNDP HDRO Extract", "description": "Fetch HDI/GII data from the UNDP HDRO Data API 2.0"},
    {"id": "structure_extract", "name": "Extract Document Structure", "description": "Extract canonical document structure from text or a file (W28E-603)"},
    {"id": "structure_document_get", "name": "Get Document Structure", "description": "Retrieve a canonical structure document with its child objects (W28E-603)"},
    {"id": "structure_outline_get", "name": "Get Document Outline", "description": "Retrieve the section-hierarchy outline of a structure document (W28E-603)"},
    {"id": "structure_corpus_create", "name": "Create Structure Corpus", "description": "Create a named corpus of structure documents (W28E-603)"},
    {"id": "structure_corpus_analyse", "name": "Analyse Structure Corpus", "description": "Derive section/style/layout/table patterns across a corpus (W28E-603)"},
    {"id": "structure_corpus_patterns_get", "name": "Get Corpus Patterns", "description": "Retrieve derived structure patterns for a corpus (W28E-603)"},
    {"id": "structure_template_generate", "name": "Generate Structure Template", "description": "Generate a structure/style template blueprint from corpus patterns (W28E-603)"},
    {"id": "structure_template_export", "name": "Export Structure Template", "description": "Export a structure template as Markdown or JSON (W28E-603)"},
    {"id": "structure_template_delete", "name": "Delete Structure Template", "description": "Delete a generated structure template through the supported lifecycle path (W28M-1603D)"},
    # W28E-1870-A PS-102 change-streaming (CSTREAM-IR-001..010) — VDB change-watch skills.
    {"id": "index_watch_create", "name": "Create VDB Change-Watch", "description": "Create a VDB profile/collection change-watch with criteria (PS-102 CSTREAM-IR-001/002)"},
    {"id": "index_watch_list", "name": "List Change-Watches", "description": "List the caller's VDB change-watches for the current tenant/profile"},
    {"id": "index_watch_status", "name": "Change-Watch Status", "description": "Return a change-watch status (state, journal depth, cursors, in-flight, throttle)"},
    {"id": "index_watch_get_batch", "name": "Get Change Batch", "description": "Retrieve a bounded batch of VDB change events since a cursor with the next cursor (backpressure-aware)"},
    {"id": "index_watch_ack", "name": "Ack Change Batch", "description": "Acknowledge change-watch progress up to a cursor, releasing an in-flight batch slot"},
    {"id": "index_watch_recover", "name": "Recover Change-Watch", "description": "Re-enquire a safe resume cursor for a change-watch without a replay storm"},
    {"id": "index_watch_pause", "name": "Pause Change-Watch", "description": "Pause a change-watch (retains cursor + journal within retention)"},
    {"id": "index_watch_resume", "name": "Resume Change-Watch", "description": "Resume a paused change-watch"},
    {"id": "index_watch_delete", "name": "Delete Change-Watch", "description": "Delete a change-watch and its journal"},
    {"id": "index_watch_test_event", "name": "Inject Test Change Event", "description": "Inject a deterministic synthetic change event into a watch's journal (test-mode, no external mutation)"},
)

AGENT_CARD: dict[str, Any] = {
    "name": "index-retriever",
    "description": "Index-retriever MCP server for document ingestion, vector search, and retrieval",
    "version": "1.0.0",
    "capabilities": {"streaming": True, "pushNotifications": False},
    "skills": [dict(skill) for skill in A2A_SKILLS],
}


class _A2ACompatibilityApp:
    """Route standalone proxy aliases through the authenticated API app."""

    _PROXY_PATHS = {
        "/": "/a2a",
        "/health": "/a2a/health",
        "/events": "/a2a/events",
        "/tasks": "/a2a/tasks",
        "/tasks/send": "/a2a/tasks",
        "/a2a/tasks/send": "/a2a/tasks",
    }

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self._app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        mapped_path = self._PROXY_PATHS.get(str(scope.get("path", "")))
        if mapped_path is not None:
            scope = dict(scope)
            scope["path"] = mapped_path
            scope["raw_path"] = mapped_path.encode("utf-8")
        await self._app(scope, receive, send)


def build_a2a_app() -> object:
    """Build the standalone A2A app with the API authentication contract."""
    from index_server.api_server import build_api_app

    api_app = build_api_app(surface_name="a2a_server")
    return _A2ACompatibilityApp(api_app)


def run_a2a_server() -> None:
    """Run the A2A server on the configured host/port."""
    app = build_a2a_app()
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("uvicorn is required to run A2A server") from exc
    binding = resolve_server_binding("a2a_server")
    uvicorn.run(app, host=binding.host, port=binding.port, log_level="info")


if __name__ == "__main__":
    run_a2a_server()
