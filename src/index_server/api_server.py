# index-retriever-mcp-server — API Server
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: HTTP API app factory using cloud_dog_api_kit.

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from cloud_dog_api_kit import create_app  # type: ignore
from fastapi import HTTPException, Request

from index_server.auth.middleware import AuthMiddleware
from index_server.mcp_server import build_registry, execute_tool
from index_tools.tools.service import IndexService


def _create_runtime_app() -> Any:
    try:
        return create_app(title="index-retriever-mcp-server", version="0.1.0")
    except TypeError:
        # Backward compatibility with older cloud_dog_api_kit signatures.
        return create_app(service_name="index-retriever-mcp-server")


def build_health_payload(service: Any | None, correlation_id: str | None = None) -> dict[str, Any]:
    request_id = correlation_id or str(uuid4())
    active_service = service or IndexService(audit_path="/tmp/index-retriever-audit-api.jsonl")
    return {
        "status": "ok",
        "correlation_id": request_id,
        "checks": {
            "vdb": active_service.backend_health_check(),
            "embedding": active_service.embedding_health_check(),
        },
    }


def handle_search(
    service: IndexService,
    auth: AuthMiddleware,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    identity = auth.authenticate(headers)
    auth.require_roles(identity, {"reader", "writer", "maintainer", "admin"})
    results = service.search(
        profile=str(payload["profile"]),
        collection=str(payload["collection"]),
        query=str(payload["query"]),
        top_k=int(payload.get("top_k", 10)),
        filters=payload.get("filters"),
    )
    return {"results": results}


def handle_ingest_text(
    service: IndexService,
    auth: AuthMiddleware,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, str]:
    identity = auth.authenticate(headers)
    auth.require_roles(identity, {"writer", "maintainer", "admin"})
    job_id = service.ingest_text(
        profile=str(payload["profile"]),
        collection=str(payload["collection"]),
        text=str(payload["text"]),
        source=str(payload.get("source", "inline")),
        actor=identity.user_id,
        idempotency_key=payload.get("idempotency_key"),
        metadata=payload.get("metadata"),
    )
    return {"job_id": job_id}


def build_api_app(service: IndexService | None = None) -> Any:
    active_service = service or IndexService(audit_path="/tmp/index-retriever-audit-api.jsonl")
    auth = AuthMiddleware()
    registry = build_registry()
    app = _create_runtime_app()

    def _auth_or_raise(headers: dict[str, str]) -> Any:
        try:
            return auth.authenticate(headers)
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    def _require_or_raise(identity: Any, roles: set[str]) -> None:
        try:
            auth.require_roles(identity, roles)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    def _headers_from_request(request: Request) -> dict[str, str]:
        return {k.lower(): v for k, v in request.headers.items()}

    def health() -> dict[str, Any]:
        return build_health_payload(active_service)

    def list_tools(request: Request) -> list[dict[str, Any]]:
        identity = _auth_or_raise(_headers_from_request(request))
        _require_or_raise(identity, {"reader", "writer", "maintainer", "admin"})
        return registry.list_tools()

    def call_tool(tool_name: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(_headers_from_request(request))
        _require_or_raise(identity, {"reader", "writer", "maintainer", "admin"})
        arguments = dict(payload)
        arguments.setdefault("actor", identity.user_id)
        try:
            return execute_tool(
                service=active_service,
                tool_name=tool_name,
                arguments=arguments,
                registry=registry,
                identity_roles=identity.roles,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    app.get("/health")(health)
    app.get("/api/v1/tools")(list_tools)
    app.post("/api/v1/tools/{tool_name}")(call_tool)
    return app


def run_api_server() -> None:
    app = build_api_app()
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required to run API server") from exc

    host = os.environ.get("CLOUD_DOG__INDEX__API_SERVER__HOST", "0.0.0.0")
    port = int(os.environ.get("CLOUD_DOG__INDEX__API_SERVER__PORT", "8686"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_api_server()
