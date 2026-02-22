# index-retriever-mcp-server — MCP Server
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: MCP transport bootstrap and tool catalogue exposure.

from __future__ import annotations

import os
from typing import Any

from cloud_dog_api_kit import create_app  # type: ignore

from index_tools.tools.registry import ToolRegistry, build_default_tool_registry
from index_tools.tools.service import IndexService


def _required_roles_for_tool(tool_name: str) -> set[str]:
    if tool_name.startswith("admin_"):
        return {"admin"}
    if tool_name.startswith("ingest_"):
        return {"writer", "maintainer", "admin"}
    if tool_name in {
        "search",
        "search_explain",
        "retrieve",
        "profiles_list",
        "profile_get",
        "collections_list",
        "collection_get",
    }:
        return {"reader", "writer", "maintainer", "admin"}
    if tool_name.startswith("job_") or tool_name == "queue_status":
        return {"writer", "maintainer", "admin"}
    if tool_name in {"delete_by_id", "delete_by_filter", "retention_run", "reindex_run"}:
        return {"maintainer", "admin"}
    if tool_name in {"backend_health_check", "embedding_health_check"}:
        return {"reader", "writer", "maintainer", "admin"}
    return {"admin"}


def list_tool_names(registry: ToolRegistry) -> list[str]:
    return [tool["name"] for tool in registry.list_tools()]


def build_registry() -> ToolRegistry:
    return build_default_tool_registry()


def execute_tool(
    service: IndexService,
    tool_name: str,
    arguments: dict[str, Any],
    registry: ToolRegistry | None = None,
    identity_roles: set[str] | None = None,
) -> dict[str, Any]:
    active_registry = registry or build_registry()
    _ = active_registry.get(tool_name)
    roles = identity_roles or {"admin"}
    required_roles = _required_roles_for_tool(tool_name)
    if not roles.intersection(required_roles):
        raise PermissionError(f"Authorisation failed for tool '{tool_name}'")

    if tool_name == "profiles_list":
        return {"profiles": service.profiles_list()}
    if tool_name == "profile_get":
        return {"profile": service.profile_get(str(arguments["profile"]))}
    if tool_name == "collections_list":
        return {"collections": service.collections_list(str(arguments.get("profile", "default")))}
    if tool_name == "admin_collection_create":
        service.admin_collection_create(
            profile=str(arguments.get("profile", "default")),
            collection=str(arguments["collection"]),
            roles=roles,
        )
        return {"status": "ok"}
    if tool_name == "admin_collection_delete":
        service.admin_collection_delete(
            profile=str(arguments.get("profile", "default")),
            collection=str(arguments["collection"]),
            roles=roles,
        )
        return {"status": "ok"}
    if tool_name == "ingest_text":
        job_id = service.ingest_text(
            profile=str(arguments["profile"]),
            collection=str(arguments["collection"]),
            text=str(arguments["text"]),
            source=str(arguments.get("source", "inline")),
            actor=str(arguments.get("actor", "mcp")),
        )
        return {"job_id": job_id, "status": "queued"}
    if tool_name == "search":
        return {
            "results": service.search(
                profile=str(arguments["profile"]),
                collection=str(arguments["collection"]),
                query=str(arguments["query"]),
                top_k=int(arguments.get("top_k", 10)),
                filters=arguments.get("filters"),
            )
        }
    if tool_name == "backend_health_check":
        return service.backend_health_check()
    if tool_name == "embedding_health_check":
        return service.embedding_health_check()
    if tool_name == "queue_status":
        return service.queue_status()
    return {"status": "ok"}


def build_mcp_app(service: IndexService | None = None, registry: ToolRegistry | None = None) -> Any:
    _ = service or IndexService(audit_path="/tmp/index-retriever-audit-mcp.jsonl")
    active_registry = registry or build_registry()
    try:
        app = create_app(title="index-retriever-mcp-server-mcp", version="0.1.0")
    except TypeError:
        app = create_app(service_name="index-retriever-mcp-server-mcp")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/mcp/tools")
    def mcp_tools() -> dict[str, Any]:
        # Keep envelope aligned with other MCP services for tool discovery.
        return {"ok": True, "data": active_registry.list_tools()}

    @app.get("/tools")
    def tools() -> dict[str, list[dict[str, Any]]]:
        return {"tools": active_registry.list_tools()}

    return app


def run_mcp_server() -> None:
    app = build_mcp_app()
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required to run MCP server") from exc

    host = os.environ.get("CLOUD_DOG__INDEX__MCP_SERVER__HOST", "0.0.0.0")
    port = int(os.environ.get("CLOUD_DOG__INDEX__MCP_SERVER__PORT", "8687"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_mcp_server()
