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

import inspect
import json
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
    create_health_router,
    register_mcp_contract,
)
from cloud_dog_api_kit.mcp import SYNC_CLASS_PROGRESS  # type: ignore
import cloud_dog_idam  # type: ignore
from cloud_dog_logging import get_audit_logger  # PS-40 tool audit
from cloud_dog_logging.audit_schema import Actor, Target
from cloud_dog_logging.correlation import get_correlation_id as get_logging_correlation_id
from cloud_dog_logging.correlation import set_correlation_id as set_logging_correlation_id

_tool_audit_logger = get_audit_logger()


def _log_tool_audit(tool_name: str, actor_id: str, outcome: str, details: dict[str, Any] | None = None) -> None:
    """PS-40 tool audit — redact document content, log metadata only."""
    safe = dict(details or {})
    for key in ("content", "text", "document", "body", "chunks"):
        safe.pop(key, None)
    _tool_audit_logger.log_crud(
        actor=Actor(type="service", id=actor_id),
        action=f"mcp.tool.{tool_name}",
        target=Target(type="mcp_tool", id=tool_name),
        outcome=outcome,
        **({"details": safe} if safe else {}),
    )
from fastapi import Request
from starlette.responses import JSONResponse

from index_server.auth.middleware import AuthMiddleware, AuthResult, _canonical_role
from index_server.logging_runtime import init_platform_logging, shutdown_platform_logging
from index_server.runtime_config import resolve_server_binding
from index_tools.config.loader import runtime_env_files
from index_tools.db import database_health, initialise_database, shutdown_database
from index_tools.queue.engine import JobTerminalStateError
from index_tools.tools.registry import ToolRegistry, build_default_tool_registry
from index_tools.tools.service import IndexService


def _mcp_audit_path() -> str:
    """Resolve MCP audit path from configured environment keys."""
    try:
        from cloud_dog_config import get_config  # type: ignore
    except Exception:
        get_config = None  # type: ignore[assignment]

    for key in ("index.mcp_audit_path", "index.storage.audit.path", "audit.log_path"):
        try:
            value = get_config(key) if get_config is not None else None
        except Exception:
            value = None
        if value is not None and str(value).strip():
            return str(value).strip()
    return "logs/index-retriever-audit-mcp.jsonl"


def _maybe_disable_timeout_middleware(app: Any) -> Any:
    """Avoid TestClient deadlocks from platform timeout middleware in local tiers."""
    process_env = os.environ
    in_pytest = process_env.get("PYTEST_CURRENT_TEST") is not None
    if not in_pytest and process_env.get("TEST_ENV_TIER", "").upper() not in {"UT", "ST"}:
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


def _compat_detail_from_error_body(payload: Any) -> str | None:
    """Surface a FastAPI-style detail field alongside MCP error envelopes."""
    if not isinstance(payload, dict) or payload.get("ok") is not False:
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    detail = error.get("message")
    if isinstance(error.get("details"), dict):
        nested_detail = error["details"].get("detail")
        if isinstance(nested_detail, str) and nested_detail.strip():
            detail = nested_detail
    if not isinstance(detail, str) or not detail.strip():
        return None
    return detail


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

    middleware = getattr(app, "middleware", None)
    if callable(middleware):
        @middleware("http")
        async def _augment_error_detail(request: Request, call_next: Callable[..., Any]) -> Any:
            response = await call_next(request)
            content_type = str(response.headers.get("content-type", ""))
            if "application/json" not in content_type:
                return response
            if not (400 <= int(getattr(response, "status_code", 200)) < 600):
                return response

            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            if not body:
                return response
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=response.status_code,
                    content=body.decode("utf-8", errors="ignore"),
                    media_type=response.media_type,
                )
            if isinstance(payload, dict) and "detail" not in payload:
                detail = _compat_detail_from_error_body(payload)
                if detail is not None:
                    payload["detail"] = detail
            headers = {
                key: value
                for key, value in response.headers.items()
                if key.lower() not in {"content-length", "content-type"}
            }
            return JSONResponse(
                status_code=response.status_code,
                content=payload,
                headers=headers,
                media_type=response.media_type,
            )
    return _maybe_disable_timeout_middleware(app)


def _required_permission_for_tool(tool_name: str) -> str:
    """Return the project permission required for an MCP tool."""
    if tool_name.startswith("admin_"):
        return "admin"
    if tool_name == "job_delete":
        return "admin"
    if tool_name.startswith("ingest_") or tool_name in {"bulk_index", "bulk_ingest"}:
        return "collection.write"
    # W28E-1870-A VDB change-watch (PS-102 §7 RBAC): read verbs need collection.read,
    # mutating lifecycle verbs (create/pause/resume/delete/test) need collection.write.
    if tool_name in {"index_watch_list", "index_watch_status", "index_watch_get_batch",
                     "index_watch_ack", "index_watch_recover"}:
        return "collection.read"
    if tool_name in {"index_watch_create", "index_watch_pause", "index_watch_resume",
                     "index_watch_delete", "index_watch_test_event"}:
        return "collection.write"
    if tool_name in {"parsers_list"}:
        return "collection.read"
    if tool_name in {"parser_test", "ocr_run", "table_extract"}:
        return "source.configure"
    if tool_name in {"extract_only"}:
        return "collection.write"
    if tool_name in {
        "search",
        "search_explain",
        "retrieve",
        "profiles_list",
        "profile_get",
        "a2a_config_events",
        "index_list",
        "collections_list",
        "list_collections",
        "collection_get",
        "source_configs_list",
        "source_config_get",
        "hdro_extract",
    }:
        return "collection.read"
    if tool_name in {
        "users_list",
        "user_get",
        "groups_list",
        "group_get",
        "api_keys_list",
    }:
        return "admin"
    if tool_name == "rbac_bindings_list":
        return "admin"
    if tool_name.startswith("job_") or tool_name == "queue_status":
        return "collection.write"
    if tool_name == "w28a_693_lifecycle_job":
        return "collection.write"
    if tool_name in {"delete_by_id", "delete_by_filter", "retention_run", "reindex_run"}:
        return "collection.write"
    if tool_name in {"backend_health_check", "embedding_health_check", "ingest_health"}:
        return "collection.read"
    if tool_name in {"file_list", "file_get", "file_download"}:
        return "collection.read"
    if tool_name == "file_upload":
        return "collection.write"
    if tool_name == "file_delete":
        return "collection.write"
    # W28E-603 document structure (Phase 1)
    if tool_name in {
        "structure_health",
        "structure_document_get",
        "structure_document_list",
        "structure_outline_get",
        "structure_pages_list",
        "structure_sections_list",
        "structure_corpus_list",
        "structure_corpus_get",
        "structure_corpus_patterns_get",
        "structure_template_get",
        "structure_template_list",
        "structure_template_export",
        "structure_template_match",
    }:
        return "collection.read"
    if tool_name in {
        "structure_document_create",
        "structure_document_delete",
        "structure_extract",
        "structure_corpus_create",
        "structure_corpus_update",
        "structure_corpus_delete",
        "structure_corpus_analyse",
        "structure_template_generate",
        "structure_template_delete",
        "structure_link_to_vdb_records",
    }:
        return "collection.write"
    return "admin"


def _enforce_tool_permission(
    tool_name: str,
    auth: AuthMiddleware,
    identity: AuthResult,
    *,
    actor_id: str,
    arguments: dict[str, Any] | None = None,
) -> None:
    """Enforce MCP/API dispatch via cloud_dog_idam permission checks.

    W28A-749: resource-bearing tools (search/retrieve/ingest/... on a collection) route
    through the resource-aware ``authorise`` (role perms ∘ RBAC bindings) so the
    group→collection cascade + default-DENY apply. Other tools keep the role-level check.
    """
    from index_server.auth import cascade

    spec = cascade.resource_for_tool(tool_name, arguments) if cascade.CASCADE_AVAILABLE else None
    if spec is not None:
        permission, resource_type, resource_id = spec
        if not auth.authorise_resource(
            identity, permission=permission, resource_type=resource_type, resource_id=resource_id
        ):
            _log_tool_audit(
                tool_name,
                actor_id,
                "denied",
                {
                    "permission": permission,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "roles": sorted(identity.roles),
                },
            )
            raise PermissionError(f"Authorisation failed for tool '{tool_name}'") from None
        return

    permission = _required_permission_for_tool(tool_name)
    try:
        auth.require_permission(identity, permission)
    except PermissionError:
        _log_tool_audit(
            tool_name,
            actor_id,
            "denied",
            {"permission": permission, "roles": sorted(identity.roles)},
        )
        raise PermissionError(f"Authorisation failed for tool '{tool_name}'") from None


def list_tool_names(registry: ToolRegistry) -> list[str]:
    """Execute list tool names."""
    return [tool["name"] for tool in registry.list_tools()]


def build_registry() -> ToolRegistry:
    """Execute build registry."""
    return build_default_tool_registry()


def _call_with_supported_kwargs(fn: Callable[..., Any], **kwargs: Any) -> Any:
    """Call a runtime hook without passing kwargs that its implementation cannot accept."""
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return fn(**kwargs)

    parameters = signature.parameters
    if any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
        return fn(**kwargs)

    supported = {key: value for key, value in kwargs.items() if key in parameters}
    return fn(**supported)


def _coerce_bool(value: Any, *, default: bool = True) -> bool:
    """Coerce a tool argument to a bool, tolerating JSON strings.

    Front-ends and A2A callers may send the flag as a native bool or as the
    string ``"true"``/``"false"``; treat the common falsey spellings as False
    and fall back to ``default`` when the value is absent/None.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"false", "0", "no", "off", ""}:
            return False
        if token in {"true", "1", "yes", "on"}:
            return True
    return default


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
            "updated_at",
            "started_at",
            "finished_at",
            "next_run_at",
            "last_heartbeat_at",
            "attempt",
            "max_attempts",
            "claimed_by",
            "correlation_id",
            "trace_id",
            "user_id",
            "request_source",
            "request_ip",
            "request_auth_method",
            "request_auth_identity",
            "request_user_agent",
            "last_error",
            "result_ref",
            "progress",
        ):
            if hasattr(job, key):
                payload[key] = getattr(job, key)

    status = payload.get("status")
    if hasattr(status, "value"):
        payload["status"] = status.value
    for timestamp_key in (
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
        "next_run_at",
        "last_heartbeat_at",
    ):
        timestamp = payload.get(timestamp_key)
        if callable(getattr(timestamp, "isoformat", None)):
            payload[timestamp_key] = timestamp.isoformat()
    return payload


_TERMINAL_JOB_STATUSES = {
    "succeeded",
    "failed",
    "cancelled",
    "timeout",
    "dead_lettered",
    "ttl_expired",
    "archived",
}


def _wait_for_job(service: IndexService, job_id: str, *, timeout_seconds: int = 50) -> Any:
    """Wait for a queued job without using the service's long queue default."""
    queue = getattr(service, "queue", None)
    wait = getattr(queue, "wait", None)
    if callable(wait):
        try:
            return wait(str(job_id), timeout_seconds=timeout_seconds)
        except TypeError:
            return wait(str(job_id))
    return service.job_wait(str(job_id))


def _stock_job_result(job: Any, *, job_id: str, timeout: bool = False, blocking_tool: str = "") -> dict[str, Any]:
    """Build the PS-95 stock-client result/error envelope for an ingest job."""
    payload = _normalise_job_payload(job)
    status = str(payload.get("status") or "unknown")
    if timeout or status not in _TERMINAL_JOB_STATUSES:
        return {
            "ok": False,
            "job_id": str(job_id),
            "status": status,
            "poll_tool": "job_get",
            "blocking_tool": blocking_tool,
            "error": {
                "code": -32000,
                "message": "Tool exceeded sync budget (50s). Job is still running.",
                "data": {"job_id": str(job_id), "status": status, "poll_tool": "job_get"},
            },
            "job": payload,
        }
    if status in {"failed", "cancelled", "timeout", "dead_lettered", "ttl_expired"}:
        return {
            "ok": False,
            "job_id": str(job_id),
            "status": status,
            "poll_tool": "job_get",
            "blocking_tool": blocking_tool,
            "error": {
                "code": -32001,
                "message": f"Ingest job ended with status {status}.",
                "data": {"job_id": str(job_id), "status": status},
            },
            "job": payload,
        }
    return {
        "ok": True,
        "job_id": str(job_id),
        "status": status,
        "poll_tool": "job_get",
        "blocking_tool": blocking_tool,
        "job": payload,
    }


def _ingest_file_job_id(service: IndexService, arguments: dict[str, Any]) -> str:
    """Submit file ingestion through existing upload/reference paths."""
    metadata = arguments.get("metadata") if isinstance(arguments.get("metadata"), dict) else None
    content = arguments.get("content")
    if content is not None and str(content) != "":
        upload_result = service.ingest_upload(
            profile=str(arguments["profile"]),
            collection=str(arguments["collection"]),
            filename=str(arguments.get("filename") or "mcp-upload.txt"),
            content=str(content).encode("utf-8"),
            actor=str(arguments.get("actor", "mcp")),
            metadata=metadata,
        )
        job_id = upload_result.get("job_id") if isinstance(upload_result, dict) else getattr(upload_result, "job_id", None)
        if not job_id:
            raise RuntimeError("ingest_upload did not return a job_id")
        return str(job_id)

    reference_path = str(arguments.get("path") or arguments.get("uri") or "").strip()
    if not reference_path:
        raise ValueError("ingest_file_async requires content, path, or uri")
    reference_result = service.ingest_reference(
        profile=str(arguments["profile"]),
        collection=str(arguments["collection"]),
        path=reference_path,
        actor=str(arguments.get("actor", "mcp")),
    )
    return str(getattr(reference_result, "job_id", reference_result))


def _job_actor_id(job: Any) -> str:
    """Return the actor that owns a normalised job record."""
    payload = _normalise_job_payload(job)
    nested_payload = payload.get("payload")
    if not isinstance(nested_payload, dict):
        nested_payload = {}
    for key in ("request_auth_identity", "user_id", "actor"):
        value = payload.get(key)
        if value not in {None, ""}:
            return str(value).strip()
    for key in ("request_auth_identity", "user_id", "actor"):
        value = nested_payload.get(key)
        if value not in {None, ""}:
            return str(value).strip()
    return ""


def _has_permission(auth: AuthMiddleware, identity: AuthResult, permission: str) -> bool:
    try:
        auth.require_permission(identity, permission)
        return True
    except PermissionError:
        return False


def _enforce_job_owner(
    service: IndexService,
    job_id: str,
    auth: AuthMiddleware,
    identity: AuthResult,
    actor_id: str,
) -> Any:
    """Load a job and enforce owner access through IDAM permissions."""
    job = service.job_get(job_id)
    if _has_permission(auth, identity, "admin"):
        return job
    if _job_actor_id(job) == actor_id:
        return job
    raise PermissionError("403 inline: non-admin users may only access their own jobs")


def _filter_jobs_for_identity(
    jobs: list[Any],
    auth: AuthMiddleware,
    identity: AuthResult,
    actor_id: str,
) -> list[Any]:
    """Filter jobs to owner-only visibility for non-admin identities."""
    if _has_permission(auth, identity, "admin"):
        return jobs
    return [job for job in jobs if _job_actor_id(job) == actor_id]


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


def _enforce_collection_permission(
    auth: AuthMiddleware,
    identity: AuthResult,
    permission: str,
    *,
    service: IndexService | None = None,
    profile: str | None = None,
    collection: str | None = None,
) -> None:
    """Enforce collection access: IDAM role-permission AND the collection's allowed_roles.

    The role-permission check gates the operation class (collection.read/write). When a
    concrete collection is supplied and it carries restricted ``allowed_roles``, the
    requester's roles must intersect them (admin always passes); otherwise access to that
    specific collection is denied (FR-05 collection-level RBAC).
    """
    # Covers: FR-05
    # W28A-749: a resource-scoped RBAC binding granting this permission on this collection
    # authorises directly (the binding IS the grant) and bypasses the role-ACL — the
    # group→collection cascade for a binding-only principal. Flat-role holders fall through to
    # the role-permission + allowed_roles checks below (preserves per-collection ACL, e.g. IT1_21).
    from index_server.auth import cascade

    if (
        cascade.CASCADE_AVAILABLE
        and profile
        and collection
        and auth.has_resource_binding(
            identity,
            permission=permission,
            resource_type=cascade.RESOURCE_TYPE_COLLECTION,
            resource_id=cascade.collection_resource_id(profile, collection),
        )
    ):
        return
    auth.require_permission(identity, permission)
    if service is None or not profile or not collection:
        return
    collection_roles = getattr(service, "collection_roles", {}) or {}
    allowed = collection_roles.get(f"{profile}:{collection}")
    if not allowed:
        return
    identity_roles = {_canonical_role(role) for role in identity.roles}
    if "admin" in identity_roles:
        return
    allowed_canonical = {_canonical_role(role) for role in allowed}
    if not (identity_roles & allowed_canonical):
        raise PermissionError(f"Authorisation failed for collection '{collection}'")


def _watch_tenant(arguments: dict[str, Any]) -> str:
    """Resolve the change-watch tenant scope from tool arguments (VDB profile)."""
    return str(arguments.get("tenant_id") or arguments.get("profile") or "default")


def _dispatch_index_watch(
    service: IndexService, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Dispatch the ``index_watch_*`` MCP tool family onto the watch adapter.

    RBAC is already enforced upstream by ``_enforce_tool_permission``; tenant/profile
    ownership is enforced inside :class:`WatchService`. Common change-stream errors
    surface as ``ValueError`` so the transport maps them to a 400/validation error.
    """
    from cloud_dog_api_kit.change_stream.errors import ChangeStreamError

    ws = service.watch_service
    tenant = _watch_tenant(arguments)
    actor = str(arguments.get("actor", "mcp"))
    try:
        if tool_name == "index_watch_create":
            return ws.create_watch(
                profile_id=str(arguments.get("profile") or arguments.get("profile_id") or "default"),
                tenant_id=tenant,
                actor=actor,
                criteria=arguments.get("criteria") if isinstance(arguments.get("criteria"), dict) else None,
                max_batch=int(arguments.get("max_batch", 100)),
                max_inflight=int(arguments.get("max_inflight", 4)),
                journal_max=int(arguments.get("journal_max", 1000)),
                journal_ttl_seconds=(
                    float(arguments["journal_ttl_seconds"])
                    if arguments.get("journal_ttl_seconds") not in (None, "")
                    else None
                ),
            )
        if tool_name == "index_watch_list":
            return {"watches": ws.list_watches(tenant_id=tenant)}
        if tool_name == "index_watch_status":
            return ws.get_status(str(arguments["watch_id"]), tenant_id=tenant)
        if tool_name == "index_watch_get_batch":
            return ws.get_batch(
                str(arguments["watch_id"]),
                tenant_id=tenant,
                since_cursor=arguments.get("since_cursor") or None,
                max_batch=int(arguments["max_batch"]) if arguments.get("max_batch") else None,
            )
        if tool_name == "index_watch_ack":
            return ws.ack(str(arguments["watch_id"]), tenant_id=tenant, ack_cursor=str(arguments["ack_cursor"]))
        if tool_name == "index_watch_recover":
            return ws.recover(
                str(arguments["watch_id"]), tenant_id=tenant, since_cursor=arguments.get("since_cursor") or None
            )
        if tool_name == "index_watch_pause":
            return ws.pause(str(arguments["watch_id"]), tenant_id=tenant)
        if tool_name == "index_watch_resume":
            return ws.resume(str(arguments["watch_id"]), tenant_id=tenant)
        if tool_name == "index_watch_delete":
            return ws.delete(str(arguments["watch_id"]), tenant_id=tenant)
        if tool_name == "index_watch_test_event":
            extra = {
                k: v
                for k, v in arguments.items()
                if k not in {"watch_id", "tenant_id", "profile", "profile_id", "actor",
                             "action", "object_ref", "_correlation_id", "_request_ip",
                             "_request_auth_method", "_request_user_agent"}
            }
            return ws.test_event(
                str(arguments["watch_id"]),
                tenant_id=tenant,
                action=str(arguments.get("action", "created")),
                object_ref=str(arguments.get("object_ref", "test")),
                **extra,
            )
    except ChangeStreamError as exc:
        # Surface the stable machine code + recovery hint through the ValueError
        # path so REST/MCP return a 400 with a deterministic error body.
        raise ValueError(json.dumps(exc.to_dict())) from exc
    except KeyError as exc:
        raise ValueError(f"missing required argument: {exc}") from exc
    raise KeyError(tool_name)


def execute_tool(
    service: IndexService,
    tool_name: str,
    arguments: dict[str, Any],
    registry: ToolRegistry | None = None,
    identity_roles: set[str] | None = None,
    auth: AuthMiddleware | None = None,
    identity: AuthResult | None = None,
) -> dict[str, Any]:
    """Execute execute tool with PS-40 audit logging."""
    # req: FR-004
    # Covers: FR-16, FR-13B
    active_registry = registry or build_registry()
    _ = active_registry.get(tool_name)
    actor_id = str(arguments.get("actor", "mcp"))
    _log_tool_audit(
        tool_name,
        actor_id,
        "success",
        {
            "phase": "invoke",
            "profile": arguments.get("profile"),
            "collection": arguments.get("collection"),
        },
    )
    active_auth = auth or AuthMiddleware()
    active_identity = identity
    if active_identity is None:
        resolved_roles = set(identity_roles or set())
        if resolved_roles:
            active_auth.sync_identity_roles(actor_id, resolved_roles)
        active_identity = AuthResult(
            user_id=actor_id,
            roles=resolved_roles,
            permissions=set(),
            token_type="direct",
        )
    roles = active_identity.roles
    _enforce_tool_permission(
        tool_name, active_auth, active_identity, actor_id=actor_id, arguments=arguments
    )

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
    if tool_name == "index_list":
        profile = str(arguments.get("profile", "default"))
        collections = service.collections_list(profile)
        return {
            "profile": profile,
            "collections": collections,
            "indexes": [{"profile": profile, "collection": collection} for collection in collections],
            "count": len(collections),
            "status": "ok",
        }
    if tool_name in {"collections_list", "list_collections"}:
        return {"collections": service.collections_list(str(arguments.get("profile", "default")))}
    if tool_name == "collection_get":
        return {
            "collection": service.collection_get(
                str(arguments.get("profile", "default")),
                str(arguments["collection"]),
            )
        }
    if tool_name == "admin_collection_create":
        requested_roles = arguments.get("allowed_roles")
        allowed_roles = set(requested_roles) if isinstance(requested_roles, list) else None
        try:
            service.admin_collection_create(
                profile=str(arguments.get("profile", "default")),
                collection=str(arguments["collection"]),
                roles=roles,
                payload=arguments,
                allowed_roles=allowed_roles,
                actor=str(arguments.get("actor", "mcp")),
            )
        except TypeError:
            service.admin_collection_create(
                profile=str(arguments.get("profile", "default")),
                collection=str(arguments["collection"]),
                roles=roles,
            )
        return {"status": "ok"}
    if tool_name == "admin_collection_update":
        return {
            "collection": service.admin_collection_update(
                profile=str(arguments.get("profile", "default")),
                collection=str(arguments["collection"]),
                roles=roles,
                updates=dict(arguments),
                actor=str(arguments.get("actor", "mcp")),
            ),
            "status": "ok",
        }
    if tool_name == "admin_collection_delete":
        try:
            service.admin_collection_delete(
                profile=str(arguments.get("profile", "default")),
                collection=str(arguments["collection"]),
                roles=roles,
                actor=str(arguments.get("actor", "mcp")),
            )
        except TypeError:
            service.admin_collection_delete(
                profile=str(arguments.get("profile", "default")),
                collection=str(arguments["collection"]),
                roles=roles,
            )
        return {"status": "ok"}
    if tool_name == "source_configs_list":
        return {"source_configs": service.source_configs_list()}
    if tool_name == "source_config_get":
        return {"source_config": service.source_config_get(str(arguments["source_id"]))}
    if tool_name == "hdro_extract":
        return service.hdro_extract(
            country_or_aggregation=str(arguments.get("country_or_aggregation", "AFG")),
            year=arguments.get("year", 2022),
            indicators=list(arguments.get("indicators", ["HDI", "GII"])),
            limit=int(arguments.get("limit", 20)),
        )
    if tool_name == "admin_source_config_create":
        return {
            "source_config": service.admin_source_config_create(
                source_id=str(arguments["source_id"]),
                roles=roles,
                payload=arguments,
                actor=str(arguments.get("actor", "mcp")),
            ),
            "status": "ok",
        }
    if tool_name == "admin_source_config_update":
        return {
            "source_config": service.admin_source_config_update(
                source_id=str(arguments["source_id"]),
                roles=roles,
                payload=arguments,
                actor=str(arguments.get("actor", "mcp")),
            ),
            "status": "ok",
        }
    if tool_name == "admin_source_config_delete":
        service.admin_source_config_delete(
            source_id=str(arguments["source_id"]),
            roles=roles,
            actor=str(arguments.get("actor", "mcp")),
        )
        return {"status": "ok"}
    if tool_name == "rbac_bindings_list":
        return {"bindings": service.rbac_bindings_list()}
    if tool_name == "admin_rbac_bind":
        return {
            "binding": service.admin_rbac_bind(
                entity_type=str(arguments["entity_type"]),
                entity_id=str(arguments["entity_id"]),
                role=str(arguments.get("role", "")),
                roles=roles,
                actor=str(arguments.get("actor", "mcp")),
                resource_type=arguments.get("resource_type"),
                resource_id=arguments.get("resource_id"),
                permission=arguments.get("permission"),
            ),
            "status": "ok",
        }
    if tool_name == "admin_rbac_unbind":
        return {
            "binding": service.admin_rbac_unbind(
                entity_type=str(arguments["entity_type"]),
                entity_id=str(arguments["entity_id"]),
                role=str(arguments.get("role", "")),
                roles=roles,
                actor=str(arguments.get("actor", "mcp")),
                resource_type=arguments.get("resource_type"),
                resource_id=arguments.get("resource_id"),
                permission=arguments.get("permission"),
            ),
            "status": "ok",
        }
    if tool_name == "ingest_upload":
        _enforce_collection_permission(active_auth, active_identity, "collection.write", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        payload = arguments.get("content", "")
        if isinstance(payload, str):
            content = payload.encode("utf-8")
        elif isinstance(payload, bytes):
            content = payload
        else:
            raise ValueError("content must be a string or bytes payload")
        return service.ingest_upload(
            profile=str(arguments["profile"]),
            collection=str(arguments["collection"]),
            filename=str(arguments["filename"]),
            content=content,
            actor=str(arguments.get("actor", "mcp")),
            metadata=arguments.get("metadata") if isinstance(arguments.get("metadata"), dict) else None,
        )
    if tool_name == "bulk_index":
        _enforce_collection_permission(active_auth, active_identity, "collection.write")
        profile = str(arguments.get("profile", "default"))
        collection = str(arguments.get("collection", "w28a_775"))
        raw_documents = arguments.get("documents")
        documents = raw_documents if isinstance(raw_documents, list) and raw_documents else [arguments]
        job_ids: list[str] = []
        for index, document in enumerate(documents):
            record = document if isinstance(document, dict) else {}
            text = str(record.get("text") or arguments.get("text") or f"bulk index document {index + 1}")
            source = str(record.get("source") or arguments.get("source") or f"bulk://{collection}/{index + 1}")
            metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else None
            job_ids.append(
                _call_with_supported_kwargs(
                    service.ingest_text,
                    profile=profile,
                    collection=collection,
                    text=text,
                    source=source,
                    actor=str(arguments.get("actor", "mcp")),
                    metadata=metadata,
                    correlation_id=arguments.get("_correlation_id") or None,
                    request_ip=arguments.get("_request_ip") or None,
                    request_auth_method=arguments.get("_request_auth_method") or None,
                    request_user_agent=arguments.get("_request_user_agent") or None,
                )
            )
        return {"job_id": job_ids[0], "job_ids": job_ids, "status": "queued", "count": len(job_ids)}
    if tool_name in {"ingest_text", "ingest_text_long"}:
        _enforce_collection_permission(active_auth, active_identity, "collection.write", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        ingest_result = _call_with_supported_kwargs(
            service.ingest_text,
            profile=str(arguments["profile"]),
            collection=str(arguments["collection"]),
            text=str(arguments["text"]),
            source=str(arguments.get("source", "inline")),
            actor=str(arguments.get("actor", "mcp")),
            idempotency_key=str(arguments["idempotency_key"]) if arguments.get("idempotency_key") else None,
            metadata=arguments.get("metadata") if isinstance(arguments.get("metadata"), dict) else None,
            correlation_id=arguments.get("_correlation_id") or None,
            request_ip=arguments.get("_request_ip") or None,
            request_auth_method=arguments.get("_request_auth_method") or None,
            request_user_agent=arguments.get("_request_user_agent") or None,
        )
        job_id = getattr(ingest_result, "job_id", ingest_result)
        job = _wait_for_job(service, str(job_id), timeout_seconds=50)
        return _stock_job_result(job, job_id=str(job_id))
    if tool_name == "ingest_file_async":
        _enforce_collection_permission(active_auth, active_identity, "collection.write", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        job_id = _ingest_file_job_id(service, arguments)
        return {
            "ok": True,
            "job_id": str(job_id),
            "status": "submitted",
            "poll_tool": "job_get",
            "blocking_tool": "ingest_file_async_blocking",
        }
    if tool_name == "ingest_file_async_blocking":
        _enforce_collection_permission(active_auth, active_identity, "collection.write", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        job_id = _ingest_file_job_id(service, arguments)
        job = _wait_for_job(service, str(job_id), timeout_seconds=50)
        return _stock_job_result(job, job_id=str(job_id), blocking_tool="ingest_file_async_blocking")
    if tool_name == "ingest_reference":
        _enforce_collection_permission(active_auth, active_identity, "collection.write", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        reference_path = str(arguments.get("path") or arguments.get("uri") or "").strip()
        if not reference_path:
            raise ValueError("ingest_reference requires path or uri")
        ingest_result = service.ingest_reference(
            profile=str(arguments["profile"]),
            collection=str(arguments["collection"]),
            path=reference_path,
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
        profile = str(arguments["profile"])
        collection = str(arguments["collection"])
        query = str(arguments["query"])
        top_k = int(arguments.get("top_k", 10))
        filters = arguments.get("filters")
        _enforce_collection_permission(
            active_auth,
            active_identity,
            "collection.read",
            service=service,
            profile=profile,
            collection=collection,
        )
        try:
            return {
                "results": service.search(
                    profile=profile,
                    collection=collection,
                    query=query,
                    top_k=top_k,
                    filters=filters,
                )
            }
        except (RuntimeError, ConnectionError, OSError, TimeoutError, KeyError) as exc:
            return {
                "results": [],
                "error": f"Search backend unavailable: {exc}",
                "status": "backend_error",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "results": [],
                "error": f"Search failed: {exc}",
                "status": "error",
            }
    if tool_name == "search_explain":
        _enforce_collection_permission(active_auth, active_identity, "collection.read", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        filters = arguments.get("filters") if isinstance(arguments.get("filters"), dict) else {}
        top_k = int(arguments.get("top_k", 10))
        query = str(arguments["query"])
        profile = str(arguments["profile"])
        collection = str(arguments["collection"])
        planned = service.search_plan(profile=profile, query=query, top_k=top_k, filters=filters)
        results = service.search(
            profile=profile,
            collection=collection,
            query=query,
            top_k=top_k,
            filters=filters,
        )
        return {
            "query": query,
            "profile": profile,
            "collection": collection,
            "plan": planned,
            "results": [
                {
                    **dict(item),
                    "similarity": {
                        "score": float(item.get("score", 0.0)),
                        "mode": str(planned.get("mode", "vector")),
                        "top_k": int(planned.get("top_k", top_k)),
                    },
                }
                for item in results
            ],
        }
    if tool_name == "retrieve":
        _enforce_collection_permission(active_auth, active_identity, "collection.read", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        # A123 fix: pass profile + collection so retrieve filters records
        # to the requested scope (RetrieveInput already requires both).
        return service.retrieve(
            str(arguments["doc_id"]),
            profile=str(arguments.get("profile")) if arguments.get("profile") else None,
            collection=str(arguments.get("collection")) if arguments.get("collection") else None,
        )
    if tool_name == "delete_by_id":
        _enforce_collection_permission(active_auth, active_identity, "collection.write", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        deleted = service.delete_by_id(
            profile=str(arguments["profile"]),
            collection=str(arguments["collection"]),
            doc_id=str(arguments["doc_id"]),
        )
        return {"deleted": bool(deleted), "status": "ok" if deleted else "not_found"}
    if tool_name == "delete_by_filter":
        _enforce_collection_permission(active_auth, active_identity, "collection.write", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        deleted = service.delete_by_filter(
            profile=str(arguments["profile"]),
            collection=str(arguments["collection"]),
            filters=arguments.get("filters") if isinstance(arguments.get("filters"), dict) else {},
        )
        return {"deleted": int(deleted), "status": "ok"}
    if tool_name == "retention_run":
        _enforce_collection_permission(active_auth, active_identity, "collection.write", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        deleted = service.retention_run(
            profile=str(arguments["profile"]),
            collection=str(arguments["collection"]),
            older_than_days=int(arguments.get("older_than_days", 0)),
        )
        return {"deleted": int(deleted), "status": "ok"}
    if tool_name == "reindex_run":
        _enforce_collection_permission(active_auth, active_identity, "collection.write", service=service, profile=str(arguments.get('profile', '')), collection=str(arguments.get('collection', '')))
        # W28E-614 XC-010: async_mode flag — when true, enqueue a JobEnvelope via
        # the existing cloud_dog_jobs-compatible queue and return {job_id, queued: true};
        # when false (default), run inline and return {documents, status}.
        async_mode = bool(arguments.get("async_mode", False))
        if async_mode:
            job_id = service.reindex_run_async(
                profile=str(arguments["profile"]),
                collection=str(arguments["collection"]),
                actor=str(arguments.get("actor", actor_id)),
            )
            return {"job_id": str(job_id), "queued": True, "status": "queued"}
        result = service.reindex_run(
            profile=str(arguments["profile"]),
            collection=str(arguments["collection"]),
        )
        if isinstance(result, dict):
            payload = dict(result)
            payload.setdefault("status", "ok")
            payload.setdefault("queued", False)
            return payload
        return {"documents": int(result), "queued": False, "status": "ok"}
    if tool_name == "bulk_ingest":
        # W28E-614 XC-010: bulk_ingest — accept a list of reference paths/uris.
        # async_mode=true (default for bulk): submit each as an ingest_reference job
        # via the existing cloud_dog_jobs-compatible queue, returning {job_id, queued: true}
        # for the umbrella enqueue plus per-item job_ids; async_mode=false: run each
        # ingest_reference inline and return aggregate results. Queued and inline paths
        # share the underlying ingest_reference handler logic.
        _enforce_collection_permission(active_auth, active_identity, "collection.read")
        references = arguments.get("references") or arguments.get("paths") or []
        if not isinstance(references, list) or not references:
            raise ValueError("bulk_ingest requires a non-empty 'references' list")
        async_mode = bool(arguments.get("async_mode", True))
        profile = str(arguments["profile"])
        collection = str(arguments["collection"])
        actor = str(arguments.get("actor", actor_id))
        per_item_jobs: list[str] = []
        per_item_results: list[dict[str, Any]] = []
        for ref in references:
            ref_str = str(ref).strip()
            if not ref_str:
                continue
            single = service.ingest_reference(
                profile=profile,
                collection=collection,
                path=ref_str,
                actor=actor,
            )
            job_id = getattr(single, "job_id", single)
            per_item_jobs.append(str(job_id))
            per_item_results.append({"reference": ref_str, "job_id": str(job_id)})
        if async_mode:
            return {
                "job_id": per_item_jobs[0] if per_item_jobs else "",
                "queued": True,
                "status": "queued",
                "items": per_item_results,
                "count": len(per_item_results),
            }
        return {
            "queued": False,
            "status": "ok",
            "items": per_item_results,
            "count": len(per_item_results),
        }
    if tool_name == "job_get":
        job = _enforce_job_owner(service, str(arguments["job_id"]), active_auth, active_identity, actor_id)
        return {"job": _normalise_job_payload(job)}
    if tool_name == "job_wait":
        _ = _enforce_job_owner(service, str(arguments["job_id"]), active_auth, active_identity, actor_id)
        job = service.job_wait(str(arguments["job_id"]))
        return {"job": _normalise_job_payload(job)}
    if tool_name == "job_list":
        status_filter = str(arguments.get("status", "")).strip().lower()
        limit = int(arguments.get("limit", 50))
        # The heavy per-job ``payload`` (full ingest text, results, thinking) can
        # reach hundreds of KB per row; a full list of it serialises to tens of MB.
        # List/table consumers (WebUI Jobs page) only need the top-level summary
        # columns (id/type/status/timestamps/actor/retry/result_ref/duration) and
        # re-fetch the full record via ``job_get`` when a row is opened. Allow such
        # callers to opt out of the payload while keeping it on by default so the
        # existing contract (A2A / automation) is preserved.
        include_payload = _coerce_bool(arguments.get("include_payload", True))
        try:
            jobs_raw = service.job_list(limit=limit)
        except TypeError:
            jobs_raw = service.job_list()
        visible_jobs = _filter_jobs_for_identity(list(jobs_raw), active_auth, active_identity, actor_id)
        jobs = [_normalise_job_payload(job) for job in visible_jobs]
        if not include_payload:
            for job in jobs:
                job.pop("payload", None)
        if status_filter:
            jobs = [job for job in jobs if str(job.get("status", "")).strip().lower() == status_filter]
        return {"jobs": jobs, "count": len(jobs)}
    if tool_name == "job_cancel":
        _ = _enforce_job_owner(service, str(arguments["job_id"]), active_auth, active_identity, actor_id)
        try:
            cancelled = service.job_cancel(str(arguments["job_id"]))
        except JobTerminalStateError as exc:
            # A terminal job (succeeded/failed/cancelled/…) is not cancellable: report a clear
            # no-op instead of flipping the record (PS-75 lifecycle integrity).
            job = _normalise_job_payload(service.job_get(str(arguments["job_id"])))
            return {
                "job": job,
                "status": exc.status,
                "cancelled": False,
                "reason": f"job is in terminal state '{exc.status}' and cannot be cancelled",
            }
        if isinstance(cancelled, bool):
            if not cancelled:
                raise ValueError("Job cancellation rejected by queue backend")
            job = {"job_id": str(arguments["job_id"]), "status": "cancelled"}
        else:
            job = _normalise_job_payload(cancelled)
        return {"job": job, "status": "cancelled", "cancelled": True}
    if tool_name == "job_retry":
        retry_fn = getattr(service, "job_retry", None)
        if not callable(retry_fn):
            raise ValueError("Job retry is not supported by this runtime")
        _ = _enforce_job_owner(service, str(arguments["job_id"]), active_auth, active_identity, actor_id)
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
    if tool_name == "job_delete":
        delete_fn = getattr(service, "job_delete", None)
        if not callable(delete_fn):
            raise ValueError("Job delete is not supported by this runtime")
        deleted = bool(delete_fn(str(arguments["job_id"])))
        if not deleted:
            raise ValueError("Job deletion rejected by queue backend")
        return {"job_id": str(arguments["job_id"]), "deleted": True, "status": "deleted"}
    if tool_name == "backend_health_check":
        return service.backend_health_check()
    if tool_name == "embedding_health_check":
        return service.embedding_health_check()
    if tool_name == "ingest_health":
        return service.ingest_health()
    # PS-78 File Lifecycle (W28C-427 IDX-SNAG-002)
    if tool_name == "file_upload":
        return service.file_upload(
            filename=str(arguments.get("filename", "upload")),
            content=str(arguments.get("content", "")),
            profile=str(arguments.get("profile", "default")),
            actor=str(arguments.get("actor", "mcp")),
            metadata=arguments.get("metadata") if isinstance(arguments.get("metadata"), dict) else None,
        )
    if tool_name == "file_list":
        return {"files": service.file_list(profile=arguments.get("profile"))}
    if tool_name == "file_get":
        return service.file_get(str(arguments["file_id"]))
    if tool_name == "file_download":
        return service.file_download(str(arguments["file_id"]))
    if tool_name == "file_delete":
        return service.file_delete(str(arguments["file_id"]), actor=str(arguments.get("actor", "mcp")))
    if tool_name == "queue_status":
        return _normalise_queue_status(service.queue_status())
    if tool_name == "w28a_693_lifecycle_job":
        return service.create_w28a_693_lifecycle_evidence_job(
            outcome=str(arguments["outcome"]),
            job_type=str(arguments.get("job_type", "ingest_text")),
            label=str(arguments.get("label", "")),
            profile=str(arguments.get("profile", "default")),
            collection=str(arguments.get("collection", "w28a_693")),
            actor=actor_id,
        )
    if tool_name == "ingest_stream_open":
        from index_server.streaming import ingest_stream_session_start as _stream_session_start
        return _stream_session_start(
            service=service,
            profile=str(arguments.get("profile", "default")),
            collection=str(arguments.get("collection", "default")),
            ordering_key=str(arguments.get("ordering_key", "")),
        )
    if tool_name == "ingest_stream_event":
        from index_server.streaming import ingest_stream_event as _stream_event
        return _stream_event(
            service=service,
            session_id=str(arguments["session_id"]),
            text=str(arguments.get("text", "")),
            actor=str(arguments.get("actor", "mcp")),
            metadata=arguments.get("metadata"),
        )
    if tool_name == "ingest_stream_close":
        from index_server.streaming import ingest_stream_close as _stream_close
        return _stream_close(service=service, session_id=str(arguments["session_id"]))
    # -- W28E-603 document structure (Phase 1) --
    if tool_name == "structure_health":
        return service.structure.health()
    if tool_name == "structure_document_create":
        payload = arguments.get("bundle", arguments)
        return service.structure.create(
            payload,
            actor=str(arguments.get("actor", "mcp")),
            roles=set(identity_roles or set()),
        )
    if tool_name == "structure_document_get":
        include = arguments.get("include")
        return service.structure.get(
            str(arguments["structure_document_id"]),
            include=list(include) if isinstance(include, (list, set, tuple)) else None,
        )
    if tool_name == "structure_document_list":
        return service.structure.list(
            profile_id=arguments.get("profile") or arguments.get("profile_id"),
            collection_id=arguments.get("collection") or arguments.get("collection_id"),
            status=arguments.get("status"),
            limit=int(arguments.get("limit", 50)),
            offset=int(arguments.get("offset", 0)),
        )
    if tool_name == "structure_document_delete":
        return service.structure.delete(
            str(arguments["structure_document_id"]),
            actor=str(arguments.get("actor", "mcp")),
            roles=set(identity_roles or set()),
        )
    if tool_name == "structure_outline_get":
        return service.structure.outline(str(arguments["structure_document_id"]))
    if tool_name == "structure_pages_list":
        return service.structure.list_pages(str(arguments["structure_document_id"]))
    if tool_name == "structure_sections_list":
        return service.structure.list_sections(str(arguments["structure_document_id"]))
    # -- W28E-603 Phase 2: extraction (W28M-1626: file/bytes path for real MinerU parsing) --
    if tool_name == "structure_extract":
        source_b64 = arguments.get("source_bytes_b64") or arguments.get("file_bytes_b64")
        if source_b64:
            import base64

            data = base64.b64decode(str(source_b64))
            return service.structure.extract_file(
                data,
                filename=str(arguments.get("source_filename") or arguments.get("filename") or "document"),
                mime_type=str(arguments.get("mime_type", "application/octet-stream")),
                profile=str(arguments.get("profile", "default")),
                collection=str(arguments.get("collection", "default")),
                provider=str(arguments.get("provider", "internal")),
                parser_services=arguments.get("parser_services"),
                options=arguments.get("options"),
                actor=str(arguments.get("actor", "mcp")),
                roles=set(identity_roles or set()),
            )
        return service.structure.extract_text(
            str(arguments.get("text", "")),
            profile=str(arguments.get("profile", "default")),
            collection=str(arguments.get("collection", "default")),
            source_uri=arguments.get("source_uri"),
            source_filename=arguments.get("source_filename"),
            provider=str(arguments.get("provider", "internal")),
            actor=str(arguments.get("actor", "mcp")),
            roles=set(identity_roles or set()),
        )
    # -- W28E-603 Phase 4: corpus --
    if tool_name == "structure_corpus_create":
        return service.structure.corpus.create(arguments.get("corpus", arguments), actor=str(arguments.get("actor", "mcp")), roles=set(identity_roles or set()))
    if tool_name == "structure_corpus_list":
        return service.structure.corpus.list(profile_id=arguments.get("profile") or arguments.get("profile_id"), limit=int(arguments.get("limit", 50)), offset=int(arguments.get("offset", 0)))
    if tool_name == "structure_corpus_get":
        return service.structure.corpus.get(str(arguments["corpus_id"]))
    if tool_name == "structure_corpus_update":
        return service.structure.corpus.update(str(arguments["corpus_id"]), arguments.get("updates", arguments), actor=str(arguments.get("actor", "mcp")), roles=set(identity_roles or set()))
    if tool_name == "structure_corpus_delete":
        return service.structure.corpus.delete(str(arguments["corpus_id"]), actor=str(arguments.get("actor", "mcp")), roles=set(identity_roles or set()))
    if tool_name == "structure_corpus_analyse":
        return service.structure.corpus.analyse(str(arguments["corpus_id"]), actor=str(arguments.get("actor", "mcp")), roles=set(identity_roles or set()))
    if tool_name == "structure_corpus_patterns_get":
        return service.structure.corpus.patterns_get(str(arguments["corpus_id"]), pattern_type=arguments.get("pattern_type"))
    # -- W28E-603 Phase 5: templates --
    if tool_name == "structure_template_generate":
        return service.structure.templates.generate(str(arguments["corpus_id"]), name=arguments.get("name"), actor=str(arguments.get("actor", "mcp")), roles=set(identity_roles or set()))
    if tool_name == "structure_template_get":
        return service.structure.templates.get(str(arguments["template_id"]))
    if tool_name == "structure_template_list":
        return service.structure.templates.list(profile_id=arguments.get("profile") or arguments.get("profile_id"), corpus_id=arguments.get("corpus_id"), limit=int(arguments.get("limit", 50)), offset=int(arguments.get("offset", 0)))
    if tool_name == "structure_template_export":
        return service.structure.templates.export(str(arguments["template_id"]), format=str(arguments.get("format", "markdown")))
    if tool_name == "structure_template_match":
        return service.structure.templates.match(
            str(arguments["template_id"]),
            str(arguments["structure_document_id"]),
        )
    if tool_name == "structure_template_delete":
        return service.structure.templates.delete(
            str(arguments["template_id"]),
            actor=str(arguments.get("actor", "mcp")),
            roles=set(identity_roles or set()),
        )
    # -- W28E-603 §25 #6: VDB linkage --
    if tool_name == "structure_link_to_vdb_records":
        return service.structure.link_to_vdb_records(
            str(arguments["structure_document_id"]),
            vdb_record_ids=arguments.get("vdb_record_ids"),
            chunk_ids=arguments.get("chunk_ids"),
            source_document_id=arguments.get("source_document_id"),
            actor=str(arguments.get("actor", "mcp")),
            roles=set(identity_roles or set()),
        )
    # W28E-1870-A VDB change-watch MCP tools (PS-102 §5.3 / CSTREAM-IR-001/002).
    if tool_name.startswith("index_watch_"):
        return _dispatch_index_watch(service, tool_name, arguments)
    return {"status": "ok"}


def build_mcp_app(service: IndexService | None = None, registry: ToolRegistry | None = None) -> Any:
    """Execute build mcp app."""
    # req: FR-001
    init_platform_logging("mcp_server")
    if cloud_dog_idam is None:  # pragma: no cover - platform package is mandatory
        raise RuntimeError("cloud_dog_idam is required")
    active_service = service or IndexService(audit_path=_mcp_audit_path())
    db_runtime = initialise_database()
    active_registry = registry or build_registry()
    auth = AuthMiddleware()
    if auth.backend_name() != "cloud_dog_idam":
        raise RuntimeError("cloud_dog_idam auth backend is required")
    if hasattr(auth, "_api_key_manager") and auth._api_key_manager is not None:
        active_service._idam_api_keys = auth._api_key_manager
    bind_idam_auth = getattr(active_service, "attach_idam_auth", None)
    if callable(bind_idam_auth):
        bind_idam_auth(auth)
    # Share user store with auth middleware for disabled-user checks when available.
    if hasattr(active_service, "users"):
        auth._user_store = active_service.users
    def _shutdown_runtime() -> None:
        active_service.close()
        shutdown_database()
        shutdown_platform_logging()

    app = _create_runtime_app(on_shutdown=_shutdown_runtime)

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

    # Platform health via create_health_router().
    _health_paths = {"/health", "/ready", "/live", "/status"}

    def _remove_existing_health_routes(router: Any) -> None:
        """Remove platform health routes across flat and nested FastAPI routers."""
        routes = getattr(router, "routes", None)
        if not isinstance(routes, list):
            return
        retained = []
        for route in routes:
            nested_router = getattr(route, "original_router", None)
            if nested_router is not None:
                _remove_existing_health_routes(nested_router)
            if getattr(route, "path", None) not in _health_paths:
                retained.append(route)
        router.routes = retained

    if hasattr(app, "router"):
        _remove_existing_health_routes(app.router)
    include_router = getattr(app, "include_router", None)
    if callable(include_router):
        include_router(create_health_router(
            application_name="index-retriever-mcp-server",
            version="0.1.0",
        ))

    def _make_tool_handler(tool_name: str) -> Any:
        """Build an auth-enforcing handler for a single tool."""

        def handler(payload: dict[str, Any], request: Request) -> dict[str, Any]:
            _sync_logging_correlation(request)
            headers = {k.lower(): v for k, v in request.headers.items()}
            try:
                identity = auth.identity_from_headers(headers)
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
            _disabled_user = active_service.users.get(identity.user_id)
            if _disabled_user is not None and not getattr(_disabled_user, 'enabled', True):
                raise UnauthenticatedError(message="User account is disabled")
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
                    auth=auth,
                    identity=identity,
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
                    required_roles=_required_permission_for_tool(tool_name),
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
            sync_class=SYNC_CLASS_PROGRESS if name == "ingest_text_long" else "sync-default",
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

    binding = resolve_server_binding("mcp_server")
    uvicorn.run(app, host=binding.host, port=binding.port, log_level="info")


if __name__ == "__main__":
    run_mcp_server()
