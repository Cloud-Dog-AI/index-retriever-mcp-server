# index-retriever-mcp-server — MCP Server
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: MCP transport bootstrap and tool catalogue exposure.

from __future__ import annotations

import os
from typing import Any

from cloud_dog_api_kit import (  # type: ignore
    ToolContract,
    UnauthenticatedError,
    UnauthorisedError,
    create_app,
    register_mcp_contract,
)
from fastapi import Request

from index_server.auth.middleware import AuthMiddleware
from index_tools.tools.registry import ToolRegistry, build_default_tool_registry
from index_tools.tools.service import IndexService


def _mcp_audit_path() -> str:
    """Resolve MCP audit path from configured environment keys."""
    return (
        os.environ.get("CLOUD_DOG__INDEX__MCP_AUDIT_PATH", "").strip()
        or os.environ.get("CLOUD_DOG__INDEX__STORAGE__AUDIT__PATH", "").strip()
        or os.environ.get("AUDIT_LOG_PATH", "").strip()
        or "logs/index-retriever-audit-mcp.jsonl"
    )


def _maybe_disable_timeout_middleware(app: Any) -> Any:
    """Avoid TestClient deadlocks from platform timeout middleware in local tiers."""
    in_pytest = "PYTEST_CURRENT_TEST" in os.environ
    if not in_pytest and os.environ.get("TEST_ENV_TIER", "").upper() not in {"UT", "ST"}:
        return app
    user_middleware = getattr(app, "user_middleware", None)
    build_stack = getattr(app, "build_middleware_stack", None)
    if not isinstance(user_middleware, list) or not callable(build_stack):
        return app
    filtered = [
        item for item in user_middleware if getattr(getattr(item, "cls", None), "__name__", "") != "TimeoutMiddleware"
    ]
    if len(filtered) == len(user_middleware):
        return app
    app.user_middleware = filtered
    app.middleware_stack = build_stack()
    return app


def _required_roles_for_tool(tool_name: str) -> set[str]:
    """Internal helper to required roles for tool."""
    if tool_name.startswith("admin_"):
        return {"admin"}
    if tool_name.startswith("ingest_"):
        return {"writer", "maintainer", "admin"}
    if tool_name in {"parsers_list"}:
        return {"reader", "writer", "maintainer", "admin"}
    if tool_name in {"parser_test", "ocr_run", "table_extract"}:
        return {"maintainer", "admin"}
    if tool_name in {"extract_only"}:
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
    """Execute list tool names."""
    return [tool["name"] for tool in registry.list_tools()]


def build_registry() -> ToolRegistry:
    """Execute build registry."""
    return build_default_tool_registry()


def execute_tool(
    service: IndexService,
    tool_name: str,
    arguments: dict[str, Any],
    registry: ToolRegistry | None = None,
    identity_roles: set[str] | None = None,
) -> dict[str, Any]:
    """Execute execute tool."""
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
        ingest_result = service.ingest_text(
            profile=str(arguments["profile"]),
            collection=str(arguments["collection"]),
            text=str(arguments["text"]),
            source=str(arguments.get("source", "inline")),
            actor=str(arguments.get("actor", "mcp")),
        )
        job_id = getattr(ingest_result, "job_id", ingest_result)
        return {"job_id": str(job_id), "status": "queued"}
    if tool_name == "parsers_list":
        return {"parsers": service.parsers_list(parser_services=arguments.get("parser_services"))}
    if tool_name == "parser_test":
        return service.parser_test(
            provider_id=str(arguments["provider_id"]),
            sample_text=str(arguments.get("sample_text", "parser health check")),
            source_uri=str(arguments.get("source_uri", "inline://parser-test.txt")),
            parser_services=arguments.get("parser_services"),
            options=arguments.get("options"),
        )
    if tool_name == "ingest_preview":
        return service.ingest_preview(
            text=str(arguments["text"]),
            source_uri=str(arguments.get("source_uri", "inline://preview.txt")),
            parser_chain=list(arguments.get("parser_chain", ["internal"])),
            parser_options=arguments.get("parser_options"),
            parser_services=arguments.get("parser_services"),
            metadata=arguments.get("metadata"),
            ocr_mode=str(arguments.get("ocr_mode", "disabled")),
            ocr_provider=str(arguments.get("ocr_provider", "")),
            table_policy=str(arguments.get("table_policy", "table_as_markdown")),
            table_json_shape=str(arguments.get("table_json_shape", "records")),
        )
    if tool_name == "extract_only":
        return service.extract_only(
            text=str(arguments["text"]),
            source_uri=str(arguments.get("source_uri", "inline://extract-only.txt")),
            parser_chain=list(arguments.get("parser_chain", ["internal"])),
            parser_options=arguments.get("parser_options"),
            parser_services=arguments.get("parser_services"),
            ocr_mode=str(arguments.get("ocr_mode", "disabled")),
            ocr_provider=str(arguments.get("ocr_provider", "")),
            table_policy=str(arguments.get("table_policy", "table_as_markdown")),
            table_json_shape=str(arguments.get("table_json_shape", "records")),
        )
    if tool_name == "ocr_run":
        return service.ocr_run(
            text=str(arguments["text"]),
            mode=str(arguments.get("mode", "auto")),
            provider_id=str(arguments.get("provider_id", "")),
            min_chars=int(arguments.get("min_chars", 200)),
            min_scanned_ratio=float(arguments.get("min_scanned_ratio", 0.5)),
            scanned_ratio=float(arguments.get("scanned_ratio", 0.0)),
        )
    if tool_name == "table_extract":
        return service.table_extract(
            text=str(arguments["text"]),
            source_uri=str(arguments.get("source_uri", "inline://table-extract.txt")),
            parser_chain=list(arguments.get("parser_chain", ["internal"])),
            parser_options=arguments.get("parser_options"),
            parser_services=arguments.get("parser_services"),
            table_policy=str(arguments.get("table_policy", "table_as_json")),
            table_json_shape=str(arguments.get("table_json_shape", "records")),
        )
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
    """Execute build mcp app."""
    active_service = service or IndexService(audit_path=_mcp_audit_path())
    active_registry = registry or build_registry()
    auth = AuthMiddleware()
    try:
        app = create_app(title="index-retriever-mcp-server-mcp", version="0.1.0")
    except TypeError:
        app = create_app(service_name="index-retriever-mcp-server-mcp")
    app = _maybe_disable_timeout_middleware(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Execute health."""
        return {"status": "ok"}

    def _make_tool_handler(tool_name: str) -> Any:
        """Build an auth-enforcing handler for a single tool."""

        def handler(payload: dict[str, Any], request: Request) -> dict[str, Any]:
            headers = {k.lower(): v for k, v in request.headers.items()}
            try:
                identity = auth.authenticate(headers)
            except PermissionError as exc:
                raise UnauthenticatedError(message=str(exc)) from exc
            arguments = dict(payload)
            arguments.setdefault("actor", identity.user_id)
            try:
                return execute_tool(
                    service=active_service,
                    tool_name=tool_name,
                    arguments=arguments,
                    registry=active_registry,
                    identity_roles=identity.roles,
                )
            except PermissionError as exc:
                raise UnauthorisedError(message=str(exc)) from exc
            except (KeyError, ValueError) as exc:
                from cloud_dog_api_kit import ValidationError as APIValidationError

                raise APIValidationError(message=str(exc)) from exc

        return handler

    tool_contracts: dict[str, ToolContract] = {}
    for tool in active_registry.list_tools():
        name = tool["name"]
        tool_contracts[name] = ToolContract(
            name=name,
            handler=_make_tool_handler(name),
            description=tool.get("description", ""),
            input_schema=tool.get("input_schema", {}),
            output_schema=tool.get("output_schema", {}),
        )

    register_mcp_contract(
        app,
        tool_contracts,
        include_legacy_tools_alias=True,
    )

    return app


def run_mcp_server() -> None:
    """Execute run mcp server."""
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
