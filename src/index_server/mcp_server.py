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

from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from cloud_dog_api_kit import (  # type: ignore
    LifecycleHooks,
    ToolContract,
    UnauthenticatedError,
    UnauthorisedError,
    create_app,
    register_mcp_contract,
)
import cloud_dog_idam  # type: ignore
from cloud_dog_logging.correlation import get_correlation_id as get_logging_correlation_id
from cloud_dog_logging.correlation import set_correlation_id as set_logging_correlation_id
from fastapi import Request

from index_server.auth.middleware import AuthMiddleware
from index_tools.db import database_health, initialise_database, shutdown_database
from index_tools.tools.registry import ToolRegistry, build_default_tool_registry
from index_tools.tools.service import IndexService


def _mcp_audit_path() -> str:
    """Resolve MCP audit path from configured environment keys."""
    return (
        os.getenv("CLOUD_DOG__INDEX__MCP_AUDIT_PATH", "").strip()
        or os.getenv("CLOUD_DOG__INDEX__STORAGE__AUDIT__PATH", "").strip()
        or os.getenv("AUDIT_LOG_PATH", "").strip()
        or "logs/index-retriever-audit-mcp.jsonl"
    )


def _maybe_disable_timeout_middleware(app: Any) -> Any:
    """Avoid TestClient deadlocks from platform timeout middleware in local tiers."""
    in_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None
    if not in_pytest and os.getenv("TEST_ENV_TIER", "").upper() not in {"UT", "ST"}:
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


def _attach_shutdown_lifespan(app: Any, on_shutdown: Callable[[], None]) -> Any:
    """Attach a shutdown callback to app lifespan for legacy app-factory variants."""
    router = getattr(app, "router", None)
    original = getattr(router, "lifespan_context", None)
    if not callable(original):
        return app

    @asynccontextmanager
    async def _lifespan(inner_app: Any) -> Any:
        async with original(inner_app):
            yield
        on_shutdown()

    router.lifespan_context = _lifespan
    return app


def _create_runtime_app(on_shutdown: Callable[[], None] | None = None) -> Any:
    """Create MCP runtime app with optional shutdown lifecycle callback."""
    lifecycle_hooks = None
    if on_shutdown is not None:
        lifecycle_hooks = LifecycleHooks(on_shutdown=lambda _app: on_shutdown())
    try:
        app = create_app(
            title="index-retriever-mcp-server-mcp",
            version="0.1.0",
            lifecycle_hooks=lifecycle_hooks,
        )
    except TypeError:
        app = create_app(service_name="index-retriever-mcp-server-mcp")
        if on_shutdown is not None:
            app = _attach_shutdown_lifespan(app, on_shutdown)
    return _maybe_disable_timeout_middleware(app)


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
        "users_list",
        "user_get",
        "groups_list",
        "group_get",
        "api_keys_list",
        "a2a_config_events",
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


def _normalise_job_payload(job: Any) -> dict[str, Any]:
    """Convert runtime job records to JSON-safe payload."""
    if job is None:
        return {}
    if isinstance(job, dict):
        payload = dict(job)
    elif callable(getattr(job, "model_dump", None)):
        payload = dict(job.model_dump())
    else:
        payload = {}
        for key in (
            "job_id",
            "profile",
            "collection",
            "job_type",
            "status",
            "ordering_key",
            "idempotency_key",
            "created_at",
        ):
            if hasattr(job, key):
                payload[key] = getattr(job, key)

    status = payload.get("status")
    if hasattr(status, "value"):
        payload["status"] = status.value
    created_at = payload.get("created_at")
    if callable(getattr(created_at, "isoformat", None)):
        payload["created_at"] = created_at.isoformat()
    return payload


def _normalise_queue_status(payload: Any) -> dict[str, Any]:
    """Normalise queue health payload with stable keys expected by tests."""
    if not isinstance(payload, dict):
        payload = {"raw_status": str(payload)}
    out = dict(payload)
    if "queue_depth" not in out:
        if "queued" in out and isinstance(out["queued"], int):
            out["queue_depth"] = int(out["queued"])
        elif "total" in out and "running" in out:
            total = int(out.get("total", 0) or 0)
            running = int(out.get("running", 0) or 0)
            out["queue_depth"] = max(0, total - running)
        else:
            out["queue_depth"] = 0
    if "active_jobs" not in out:
        out["active_jobs"] = int(out.get("running", 0) or 0)
    if "worker_count" not in out:
        out["worker_count"] = int(out.get("workers", 1) or 1)
    return out


def _enforce_collection_acl(service: IndexService, roles: set[str], arguments: dict[str, Any]) -> None:
    """Enforce per-collection RBAC when service exposes collection ACL checks."""
    # Covers: FR-05
    checker = getattr(service, "is_collection_role_allowed", None)
    if not callable(checker):
        return
    collection = str(arguments.get("collection", "")).strip()
    if not collection:
        return
    profile = str(arguments.get("profile", "default"))
    if checker(profile, collection, roles):
        return
    raise PermissionError(f"Authorisation failed for collection '{collection}'")


def execute_tool(
    service: IndexService,
    tool_name: str,
    arguments: dict[str, Any],
    registry: ToolRegistry | None = None,
    identity_roles: set[str] | None = None,
) -> dict[str, Any]:
    """Execute execute tool."""
    # Covers: FR-16, FR-13B
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
    if tool_name == "admin_profile_create":
        return {
            "profile": service.admin_profile_create(
                profile=str(arguments["profile"]),
                roles=roles,
                config=arguments.get("config") if isinstance(arguments.get("config"), dict) else None,
                actor=str(arguments.get("actor", "mcp")),
            ),
            "status": "ok",
        }
    if tool_name == "admin_profile_update":
        updates = arguments.get("config") if isinstance(arguments.get("config"), dict) else dict(arguments)
        updates.pop("profile", None)
        updates.pop("actor", None)
        updates.pop("collection", None)
        service.admin_profile_update(
            profile=str(arguments["profile"]),
            roles=roles,
            updates=updates,
            actor=str(arguments.get("actor", "mcp")),
        )
        return {"status": "ok"}
    if tool_name == "admin_profile_delete":
        service.admin_profile_delete(
            profile=str(arguments["profile"]),
            roles=roles,
            actor=str(arguments.get("actor", "mcp")),
        )
        return {"status": "ok"}
    if tool_name == "users_list":
        return {"users": service.users_list()}
    if tool_name == "user_get":
        return {"user": service.user_get(str(arguments["user_id"]))}
    if tool_name == "admin_user_create":
        return {
            "user": service.admin_user_create(
                user_id=str(arguments["user_id"]),
                roles=roles,
                payload=arguments,
                actor=str(arguments.get("actor", "mcp")),
            ),
            "status": "ok",
        }
    if tool_name == "admin_user_update":
        return {
            "user": service.admin_user_update(
                user_id=str(arguments["user_id"]),
                roles=roles,
                payload=arguments,
                actor=str(arguments.get("actor", "mcp")),
            ),
            "status": "ok",
        }
    if tool_name == "admin_user_delete":
        service.admin_user_delete(
            user_id=str(arguments["user_id"]),
            roles=roles,
            actor=str(arguments.get("actor", "mcp")),
        )
        return {"status": "ok"}
    if tool_name == "groups_list":
        return {"groups": service.groups_list()}
    if tool_name == "group_get":
        return {"group": service.group_get(str(arguments["group_id"]))}
    if tool_name == "admin_group_create":
        return {
            "group": service.admin_group_create(
                group_id=str(arguments["group_id"]),
                roles=roles,
                payload=arguments,
                actor=str(arguments.get("actor", "mcp")),
            ),
            "status": "ok",
        }
    if tool_name == "admin_group_update":
        return {
            "group": service.admin_group_update(
                group_id=str(arguments["group_id"]),
                roles=roles,
                payload=arguments,
                actor=str(arguments.get("actor", "mcp")),
            ),
            "status": "ok",
        }
    if tool_name == "admin_group_delete":
        service.admin_group_delete(
            group_id=str(arguments["group_id"]),
            roles=roles,
            actor=str(arguments.get("actor", "mcp")),
        )
        return {"status": "ok"}
    if tool_name == "api_keys_list":
        return {"api_keys": service.api_keys_list()}
    if tool_name == "admin_api_key_create":
        return {
            "api_key": service.admin_api_key_create(
                roles=roles,
                payload=arguments,
                actor=str(arguments.get("actor", "mcp")),
            ),
            "status": "ok",
        }
    if tool_name == "admin_api_key_revoke":
        return {
            "api_key": service.admin_api_key_revoke(
                key_id=str(arguments["key_id"]),
                roles=roles,
                actor=str(arguments.get("actor", "mcp")),
            ),
            "status": "ok",
        }
    if tool_name == "a2a_config_events":
        return {"events": service.a2a_config_events()}
    if tool_name == "collections_list":
        return {"collections": service.collections_list(str(arguments.get("profile", "default")))}
    if tool_name == "admin_collection_create":
        requested_roles = arguments.get("allowed_roles")
        allowed_roles = set(requested_roles) if isinstance(requested_roles, list) else None
        try:
            service.admin_collection_create(
                profile=str(arguments.get("profile", "default")),
                collection=str(arguments["collection"]),
                roles=roles,
                allowed_roles=allowed_roles,
            )
        except TypeError:
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
        _enforce_collection_acl(service, roles, arguments)
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
        _enforce_collection_acl(service, roles, arguments)
        return {
            "results": service.search(
                profile=str(arguments["profile"]),
                collection=str(arguments["collection"]),
                query=str(arguments["query"]),
                top_k=int(arguments.get("top_k", 10)),
                filters=arguments.get("filters"),
            )
        }
    if tool_name == "job_get":
        job = service.job_get(str(arguments["job_id"]))
        return {"job": _normalise_job_payload(job)}
    if tool_name == "job_wait":
        job = service.job_wait(str(arguments["job_id"]))
        return {"job": _normalise_job_payload(job)}
    if tool_name == "job_list":
        status_filter = str(arguments.get("status", "")).strip().lower()
        limit = int(arguments.get("limit", 50))
        try:
            jobs_raw = service.job_list(limit=limit)
        except TypeError:
            jobs_raw = service.job_list()
        jobs = [_normalise_job_payload(job) for job in list(jobs_raw)]
        if status_filter:
            jobs = [job for job in jobs if str(job.get("status", "")).strip().lower() == status_filter]
        return {"jobs": jobs, "count": len(jobs)}
    if tool_name == "job_cancel":
        cancelled = service.job_cancel(str(arguments["job_id"]))
        if isinstance(cancelled, bool):
            if not cancelled:
                raise ValueError("Job cancellation rejected by queue backend")
            job = {"job_id": str(arguments["job_id"]), "status": "cancelled"}
        else:
            job = _normalise_job_payload(cancelled)
        return {"job": job, "status": "cancelled"}
    if tool_name == "job_retry":
        retry_fn = getattr(service, "job_retry", None)
        if not callable(retry_fn):
            raise ValueError("Job retry is not supported by this runtime")
        retried = retry_fn(str(arguments["job_id"]))
        if isinstance(retried, bool):
            if not retried:
                raise ValueError("Job retry rejected by queue backend")
            try:
                job = _normalise_job_payload(service.job_get(str(arguments["job_id"])))
            except Exception:
                job = {"job_id": str(arguments["job_id"]), "status": "queued"}
        else:
            job = _normalise_job_payload(retried)
        return {"job": job, "status": str(job.get("status", "queued"))}
    if tool_name == "backend_health_check":
        return service.backend_health_check()
    if tool_name == "embedding_health_check":
        return service.embedding_health_check()
    if tool_name == "queue_status":
        return _normalise_queue_status(service.queue_status())
    return {"status": "ok"}


def build_mcp_app(service: IndexService | None = None, registry: ToolRegistry | None = None) -> Any:
    """Execute build mcp app."""
    if cloud_dog_idam is None:  # pragma: no cover - platform package is mandatory
        raise RuntimeError("cloud_dog_idam is required")
    active_service = service or IndexService(audit_path=_mcp_audit_path())
    db_runtime = initialise_database()
    active_registry = registry or build_registry()
    auth = AuthMiddleware()
    if auth.backend_name() != "cloud_dog_idam":
        raise RuntimeError("cloud_dog_idam auth backend is required")
    bind_auth_api_keys = getattr(active_service, "attach_auth_api_keys", None)
    if callable(bind_auth_api_keys):
        bind_auth_api_keys(auth.api_keys)
    app = _create_runtime_app(on_shutdown=shutdown_database)

    def _sync_logging_correlation(request: Request) -> str:
        correlation_id = str(getattr(request.state, "correlation_id", "") or "").strip()
        if not correlation_id:
            correlation_id = request.headers.get("x-correlation-id", "").strip()
        if correlation_id:
            set_logging_correlation_id(correlation_id)
        return get_logging_correlation_id()

    def _request_ip(request: Request) -> str | None:
        client = getattr(request, "client", None)
        host = getattr(client, "host", None)
        return str(host) if host else None

    def _request_user_agent(request: Request) -> str | None:
        user_agent = request.headers.get("user-agent", "").strip()
        return user_agent or None

    def _log_auth_event(
        request: Request,
        *,
        actor: str,
        outcome: str,
        action: str,
        roles: set[str] | None = None,
        auth_mechanism: str = "",
        reason: str = "",
        required_roles: str = "",
    ) -> None:
        audit_logger = getattr(active_service, "audit_logger", None)
        log_security_event = getattr(audit_logger, "log_security_event", None)
        if not callable(log_security_event):
            return
        log_security_event(
            actor=actor,
            action=action,
            target_type="mcp_endpoint",
            target_id=request.url.path,
            outcome=outcome,
            roles=roles,
            actor_type="user" if actor != "anonymous" else "system",
            ip=_request_ip(request),
            user_agent=_request_user_agent(request),
            method=request.method,
            auth_mechanism=auth_mechanism,
            reason=reason,
            required_roles=required_roles,
        )

    @app.get("/health")
    def health(request: Request = None) -> dict[str, str]:
        """Execute health."""
        if request is not None:
            _sync_logging_correlation(request)
        _ = database_health(db_runtime)
        return {"status": "ok"}

    def _make_tool_handler(tool_name: str) -> Any:
        """Build an auth-enforcing handler for a single tool."""

        def handler(payload: dict[str, Any], request: Request) -> dict[str, Any]:
            _sync_logging_correlation(request)
            headers = {k.lower(): v for k, v in request.headers.items()}
            try:
                identity = auth.authenticate(headers)
            except PermissionError as exc:
                _log_auth_event(
                    request,
                    actor="anonymous",
                    outcome="failure",
                    action="authenticate",
                    auth_mechanism="api_key_or_jwt",
                    reason=str(exc),
                )
                raise UnauthenticatedError(message=str(exc)) from exc
            _log_auth_event(
                request,
                actor=identity.user_id,
                outcome="success",
                action="authenticate",
                roles=identity.roles,
                auth_mechanism=identity.token_type,
            )
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
                _log_auth_event(
                    request,
                    actor=identity.user_id,
                    outcome="denied",
                    action="authorise",
                    roles=identity.roles,
                    auth_mechanism=identity.token_type,
                    reason=str(exc),
                    required_roles=",".join(sorted(_required_roles_for_tool(tool_name))),
                )
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

    app.state.db_runtime = db_runtime

    return app


def run_mcp_server() -> None:
    """Execute run mcp server."""
    app = build_mcp_app()
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required to run MCP server") from exc

    host = os.getenv("CLOUD_DOG__INDEX__MCP_SERVER__HOST", "0.0.0.0")
    port = int(os.getenv("CLOUD_DOG__INDEX__MCP_SERVER__PORT", "8687"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_mcp_server()
