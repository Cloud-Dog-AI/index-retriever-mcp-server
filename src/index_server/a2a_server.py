# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""A2A server entrypoint for the authenticated A2A surface.

W28C-427 IDX-SNAG-003: provides agent card at /.well-known/agent.json
with skills for ingest, search, retrieve, admin, and source-config.
"""

from __future__ import annotations

import json
from typing import Any

from index_server.api_server import build_api_app
from index_server.runtime_config import resolve_server_binding

AGENT_CARD: dict[str, Any] = {
    "name": "index-retriever",
    "description": "Index-retriever MCP server for document ingestion, vector search, and retrieval",
    "version": "1.0.0",
    "capabilities": {"streaming": True, "pushNotifications": False},
    "skills": [
        {"id": "ingest_text", "name": "Ingest Text", "description": "Ingest text content into a profiled collection with embedding and indexing"},
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
        {"id": "structure_extract", "name": "Extract Document Structure", "description": "Extract canonical document structure (pages/blocks/sections/styles/tables) from text or a file (W28E-603)"},
        {"id": "structure_document_get", "name": "Get Document Structure", "description": "Retrieve a canonical structure document with its child objects (W28E-603)"},
        {"id": "structure_outline_get", "name": "Get Document Outline", "description": "Retrieve the section-hierarchy outline of a structure document (W28E-603)"},
        {"id": "structure_corpus_create", "name": "Create Structure Corpus", "description": "Create a named corpus of structure documents for cross-document analysis (W28E-603)"},
        {"id": "structure_corpus_analyse", "name": "Analyse Structure Corpus", "description": "Derive section/style/layout/table patterns across a corpus (W28E-603)"},
        {"id": "structure_corpus_patterns_get", "name": "Get Corpus Patterns", "description": "Retrieve derived structure patterns for a corpus (W28E-603)"},
        {"id": "structure_template_generate", "name": "Generate Structure Template", "description": "Generate a reusable structure/style template blueprint from corpus patterns (W28E-603)"},
        {"id": "structure_template_export", "name": "Export Structure Template", "description": "Export a structure template as Markdown or JSON (W28E-603)"},
    ],
}


def build_a2a_app() -> object:
    """Build the A2A server app with agent card endpoint."""
    app = build_api_app(surface_name="a2a_server")

    try:
        from fastapi import Request
        from fastapi.responses import JSONResponse

        @app.get("/.well-known/agent.json")
        async def agent_card(request: Request) -> JSONResponse:
            """Return the A2A agent card per PS-72."""
            return JSONResponse(content=AGENT_CARD)

        @app.get("/a2a/health")
        async def a2a_health(request: Request) -> JSONResponse:
            """Return A2A health status."""
            return JSONResponse(content={"status": "ok", "service": "index-retriever", "surface": "a2a"})
    except ImportError:
        pass

    return app


def run_a2a_server() -> None:
    """Run the A2A server on the configured host/port."""
    app = build_a2a_app()
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required to run A2A server") from exc

    binding = resolve_server_binding("a2a_server")
    uvicorn.run(app, host=binding.host, port=binding.port, log_level="info")


if __name__ == "__main__":
    run_a2a_server()
