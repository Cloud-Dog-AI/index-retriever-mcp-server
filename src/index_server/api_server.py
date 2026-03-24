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
import json
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from cloud_dog_api_kit import LifecycleHooks, create_app  # type: ignore
from cloud_dog_logging.correlation import get_correlation_id as get_logging_correlation_id
from cloud_dog_logging.correlation import set_correlation_id as set_logging_correlation_id
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from index_server.admin_ui import admin_ui_script, admin_ui_styles, profiles_page, security_page
from index_server.auth.middleware import AuthMiddleware
from index_server.mcp_server import build_registry, execute_tool
from index_tools.db import (
    PlatformDatabaseRuntime,
    database_health,
    initialise_database,
    shutdown_database,
)
from index_tools.tools.service import IndexService

_CANONICAL_API_BASE_PATH = "/app/v1"
_LEGACY_API_BASE_PATH = "/api/v1"
_CANONICAL_A2A_BASE_PATH = "/a2a"
_SPA_RESERVED_PREFIXES = (
    "api",
    "app",
    "a2a",
    "mcp",
    "admin",
    "assets",
    "health",
    "runtime-config.js",
    "docs",
    "openapi.json",
)


def _api_audit_path() -> str:
    """Resolve API audit path from configured environment keys."""
    return (
        os.getenv("CLOUD_DOG__INDEX__API_AUDIT_PATH", "").strip()
        or os.getenv("CLOUD_DOG__INDEX__STORAGE__AUDIT__PATH", "").strip()
        or os.getenv("AUDIT_LOG_PATH", "").strip()
        or "logs/index-retriever-audit-api.jsonl"
    )


def _ui_dist_dir() -> Path:
    """Resolve the built SPA distribution directory."""
    return Path(__file__).resolve().parents[2] / "ui" / "dist"


def _ui_assets_dir() -> Path:
    """Resolve the built SPA assets directory."""
    return _ui_dist_dir() / "assets"


def _ui_index_path() -> Path:
    """Resolve the built SPA index file."""
    return _ui_dist_dir() / "index.html"


def _runtime_config_payload() -> dict[str, str]:
    """Build runtime config for the SPA bootstrap."""
    return {
        "ENV": os.getenv("CLOUD_DOG_ENVIRONMENT", "dev"),
        "API_BASE_URL": os.getenv("CLOUD_DOG__INDEX__UI__API_BASE_URL", "").strip() or "${window.location.origin}",
        "AUTH_MODE": os.getenv("CLOUD_DOG__INDEX__UI__AUTH_MODE", "api_key"),
        "APP_VERSION": os.getenv("CLOUD_DOG__INDEX__UI__APP_VERSION", "dev"),
        "DEFAULT_PROFILE": os.getenv("CLOUD_DOG__INDEX__UI__DEFAULT_PROFILE", "default"),
        "DEFAULT_COLLECTION": os.getenv("CLOUD_DOG__INDEX__UI__DEFAULT_COLLECTION", "w12_documents"),
    }


def _runtime_config_response() -> Response:
    """Render the runtime config bootstrap script."""
    payload = _runtime_config_payload()
    api_base_value = payload["API_BASE_URL"]
    api_base_js = "`" + api_base_value + "`" if api_base_value.startswith("${") else json.dumps(api_base_value)
    lines = [
        "window.__RUNTIME_CONFIG__ = {",
        f'  ENV: {json.dumps(payload["ENV"])},',
        f"  API_BASE_URL: {api_base_js},",
        f'  AUTH_MODE: {json.dumps(payload["AUTH_MODE"])},',
        f'  APP_VERSION: {json.dumps(payload["APP_VERSION"])},',
        f'  DEFAULT_PROFILE: {json.dumps(payload["DEFAULT_PROFILE"])},',
        f'  DEFAULT_COLLECTION: {json.dumps(payload["DEFAULT_COLLECTION"])}',
        "};",
    ]
    return Response(content="\n".join(lines), media_type="application/javascript")


def _spa_not_built_response() -> HTMLResponse:
    """Return a stable 503 response when the SPA bundle is unavailable."""
    return HTMLResponse(content="<h1>UI not built</h1>", status_code=503)


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
    """Internal helper to create runtime app."""
    lifecycle_hooks = None
    if on_shutdown is not None:
        lifecycle_hooks = LifecycleHooks(on_shutdown=lambda _app: on_shutdown())
    try:
        app = create_app(
            title="index-retriever-mcp-server",
            version="0.1.0",
            lifecycle_hooks=lifecycle_hooks,
        )
    except TypeError:
        # Backward compatibility with older cloud_dog_api_kit signatures.
        app = create_app(service_name="index-retriever-mcp-server")
        if on_shutdown is not None:
            app = _attach_shutdown_lifespan(app, on_shutdown)
    return _maybe_disable_timeout_middleware(app)


def build_health_payload(
    service: Any | None,
    correlation_id: str | None = None,
    db_runtime: PlatformDatabaseRuntime | None = None,
) -> dict[str, Any]:
    """Execute build health payload."""
    request_id = correlation_id or get_logging_correlation_id()
    active_service = service or IndexService(audit_path=_api_audit_path())
    db_probe = database_health(db_runtime)
    return {
        "status": "ok",
        "correlation_id": request_id,
        "checks": {
            "db": db_probe,
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
    """Execute handle search."""
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
    """Execute handle ingest text."""
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
    """Execute build api app."""
    # Covers: FR-01, FR-01A, FR-17
    active_service = service or IndexService(audit_path=_api_audit_path())
    db_runtime = initialise_database()
    auth = AuthMiddleware()
    bind_auth_api_keys = getattr(active_service, "attach_auth_api_keys", None)
    if callable(bind_auth_api_keys):
        bind_auth_api_keys(auth.api_keys)
    registry = build_registry()
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
            target_type="endpoint",
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

    def _auth_or_raise(request: Request, headers: dict[str, str]) -> Any:
        """Internal helper to auth or raise."""
        _sync_logging_correlation(request)
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
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        _log_auth_event(
            request,
            actor=identity.user_id,
            outcome="success",
            action="authenticate",
            roles=identity.roles,
            auth_mechanism=identity.token_type,
        )
        return identity

    def _require_or_raise(request: Request, identity: Any, roles: set[str]) -> None:
        """Internal helper to require or raise."""
        try:
            auth.require_roles(identity, roles)
        except PermissionError as exc:
            _log_auth_event(
                request,
                actor=identity.user_id,
                outcome="denied",
                action="authorise",
                roles=identity.roles,
                auth_mechanism=identity.token_type,
                reason=str(exc),
                required_roles=",".join(sorted(roles)),
            )
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    def _a2a_auth_or_raise(request: Request, headers: dict[str, str]) -> Any:
        """Enforce A2A auth contract using shared API-key authority."""
        # Covers: FR-01B
        _sync_logging_correlation(request)
        try:
            identity = auth.authenticate_api_key(headers)
        except PermissionError as exc:
            _log_auth_event(
                request,
                actor="anonymous",
                outcome="failure",
                action="authenticate",
                auth_mechanism="api_key",
                reason=str(exc),
            )
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        _log_auth_event(
            request,
            actor=identity.user_id,
            outcome="success",
            action="authenticate",
            roles=identity.roles,
            auth_mechanism=identity.token_type,
        )
        return identity

    def _headers_from_request(request: Request) -> dict[str, str]:
        """Internal helper to headers from request."""
        _sync_logging_correlation(request)
        return {k.lower(): v for k, v in request.headers.items()}

    def health(request: Request = None) -> dict[str, Any]:
        """Execute health."""
        correlation_id = _sync_logging_correlation(request) if request is not None else get_logging_correlation_id()
        return build_health_payload(active_service, correlation_id=correlation_id, db_runtime=db_runtime)

    def a2a_root(request: Request) -> dict[str, Any]:
        """Execute a2a root."""
        _ = _a2a_auth_or_raise(request, _headers_from_request(request))
        return {
            "status": "ok",
            "service": "index-retriever-a2a",
            "base_path": _CANONICAL_A2A_BASE_PATH,
            "auth": auth.auth_health(),
        }

    def a2a_health(request: Request) -> dict[str, Any]:
        """Execute a2a health."""
        _ = _a2a_auth_or_raise(request, _headers_from_request(request))
        return build_health_payload(active_service, correlation_id=get_logging_correlation_id(), db_runtime=db_runtime)

    def a2a_events(request: Request) -> dict[str, Any]:
        """Expose configuration change events via the A2A interface."""
        _ = _a2a_auth_or_raise(request, _headers_from_request(request))
        return {"events": active_service.a2a_config_events()}

    def runtime_config() -> Response:
        """Serve the runtime config bootstrap for the SPA."""
        return _runtime_config_response()

    def admin_ui_root() -> HTMLResponse:
        """Serve the legacy admin UI root while parity work remains incomplete."""
        return HTMLResponse(content=profiles_page())

    def admin_ui_profiles() -> HTMLResponse:
        """Serve the legacy profile management page."""
        return HTMLResponse(content=profiles_page())

    def admin_ui_security() -> HTMLResponse:
        """Serve the legacy security management page."""
        return HTMLResponse(content=security_page())

    def admin_ui_app_js() -> Response:
        """Serve the legacy admin UI client script."""
        return Response(content=admin_ui_script(), media_type="application/javascript")

    def admin_ui_styles_css() -> Response:
        """Serve the legacy admin UI stylesheet."""
        return Response(content=admin_ui_styles(), media_type="text/css")

    def spa_index() -> Response:
        """Serve the SPA entrypoint."""
        index_path = _ui_index_path()
        if not index_path.exists():
            return _spa_not_built_response()
        return FileResponse(index_path)

    def spa_fallback(path: str) -> Response:
        """Serve the SPA entrypoint for client-routed paths."""
        if path.startswith(_SPA_RESERVED_PREFIXES):
            raise HTTPException(status_code=404, detail="Not found")
        if "." in path.rsplit("/", 1)[-1]:
            raise HTTPException(status_code=404, detail="Not found")
        return spa_index()

    def list_tools(request: Request) -> list[dict[str, Any]]:
        """Execute list tools."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return registry.list_tools()

    def call_tool(tool_name: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        """Execute call tool."""
        # Covers: FR-17
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
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

    def admin_profiles_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        profiles = [
            active_service.profile_get(profile) | {"profile": profile}
            for profile in active_service.profiles_list()
        ]
        return {"profiles": profiles}

    def admin_profiles_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        profile_name = str(payload["profile"])
        config = payload.get("config") if isinstance(payload.get("config"), dict) else payload.get("profile_config", {})
        profile = active_service.admin_profile_create(
            profile=profile_name,
            roles=identity.roles,
            config=config if isinstance(config, dict) else {},
            actor=identity.user_id,
        )
        return {"profile": profile_name, "config": profile}

    def admin_profiles_get(profile_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return {"profile": profile_id, "config": active_service.profile_get(profile_id)}

    def admin_profiles_update(profile_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        updates = payload.get("config") if isinstance(payload.get("config"), dict) else payload
        if not isinstance(updates, dict):
            raise HTTPException(status_code=400, detail="Invalid profile payload")
        profile = active_service.admin_profile_update(
            profile=profile_id,
            roles=identity.roles,
            updates=dict(updates),
            actor=identity.user_id,
        )
        return {"profile": profile_id, "config": profile}

    def admin_profiles_delete(profile_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        active_service.admin_profile_delete(profile=profile_id, roles=identity.roles, actor=identity.user_id)
        return {"status": "ok", "profile": profile_id}

    def admin_users_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return {"users": active_service.users_list()}

    def admin_users_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        user_id = str(payload["user_id"])
        return {
            "user": active_service.admin_user_create(
                user_id=user_id,
                roles=identity.roles,
                payload=payload,
                actor=identity.user_id,
            )
        }

    def admin_users_get(user_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return {"user": active_service.user_get(user_id)}

    def admin_users_update(user_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        return {
            "user": active_service.admin_user_update(
                user_id=user_id,
                roles=identity.roles,
                payload=payload,
                actor=identity.user_id,
            )
        }

    def admin_users_delete(user_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        active_service.admin_user_delete(user_id=user_id, roles=identity.roles, actor=identity.user_id)
        return {"status": "ok", "user_id": user_id}

    def admin_groups_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return {"groups": active_service.groups_list()}

    def admin_groups_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        group_id = str(payload["group_id"])
        return {
            "group": active_service.admin_group_create(
                group_id=group_id,
                roles=identity.roles,
                payload=payload,
                actor=identity.user_id,
            )
        }

    def admin_groups_get(group_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return {"group": active_service.group_get(group_id)}

    def admin_groups_update(group_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        return {
            "group": active_service.admin_group_update(
                group_id=group_id,
                roles=identity.roles,
                payload=payload,
                actor=identity.user_id,
            )
        }

    def admin_groups_delete(group_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        active_service.admin_group_delete(group_id=group_id, roles=identity.roles, actor=identity.user_id)
        return {"status": "ok", "group_id": group_id}

    def admin_api_keys_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return {"api_keys": active_service.api_keys_list()}

    def admin_api_keys_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        return {
            "api_key": active_service.admin_api_key_create(
                roles=identity.roles,
                payload=payload,
                actor=identity.user_id,
            )
        }

    def admin_api_keys_delete(key_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        return {
            "api_key": active_service.admin_api_key_revoke(
                key_id=key_id,
                roles=identity.roles,
                actor=identity.user_id,
            )
        }

    assets_dir = _ui_assets_dir()
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="ui-assets")

    app.get("/runtime-config.js")(runtime_config)
    app.get("/health")(health)
    app.get("/api/health")(health)
    app.get(f"{_CANONICAL_API_BASE_PATH}/health")(health)
    app.get(_CANONICAL_A2A_BASE_PATH)(a2a_root)
    app.get(f"{_CANONICAL_A2A_BASE_PATH}/health")(a2a_health)
    app.get(f"{_CANONICAL_A2A_BASE_PATH}/events")(a2a_events)
    app.get("/admin/ui")(admin_ui_root)
    app.get("/admin/ui/profiles")(admin_ui_profiles)
    app.get("/admin/ui/security")(admin_ui_security)
    app.get("/admin/ui/app.js")(admin_ui_app_js)
    app.get("/admin/ui/styles.css")(admin_ui_styles_css)
    for base_path in (_CANONICAL_API_BASE_PATH, _LEGACY_API_BASE_PATH):
        app.get(f"{base_path}/tools")(list_tools)
        app.post(f"{base_path}/tools/{{tool_name}}")(call_tool)

    app.get("/admin/profiles")(admin_profiles_list)
    app.post("/admin/profiles")(admin_profiles_create)
    app.get("/admin/profiles/{profile_id}")(admin_profiles_get)
    app.put("/admin/profiles/{profile_id}")(admin_profiles_update)
    app.delete("/admin/profiles/{profile_id}")(admin_profiles_delete)
    app.get("/admin/users")(admin_users_list)
    app.post("/admin/users")(admin_users_create)
    app.get("/admin/users/{user_id}")(admin_users_get)
    app.put("/admin/users/{user_id}")(admin_users_update)
    app.delete("/admin/users/{user_id}")(admin_users_delete)
    app.get("/admin/groups")(admin_groups_list)
    app.post("/admin/groups")(admin_groups_create)
    app.get("/admin/groups/{group_id}")(admin_groups_get)
    app.put("/admin/groups/{group_id}")(admin_groups_update)
    app.delete("/admin/groups/{group_id}")(admin_groups_delete)
    app.get("/admin/api-keys")(admin_api_keys_list)
    app.post("/admin/api-keys")(admin_api_keys_create)
    app.delete("/admin/api-keys/{key_id}")(admin_api_keys_delete)
    app.get("/")(spa_index)
    app.get("/{path:path}")(spa_fallback)

    app.state.db_runtime = db_runtime

    return app


def run_api_server() -> None:
    """Execute run api server."""
    app = build_api_app()
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required to run API server") from exc

    host = os.getenv("CLOUD_DOG__INDEX__API_SERVER__HOST", "0.0.0.0")
    port = int(os.getenv("CLOUD_DOG__INDEX__API_SERVER__PORT", "8686"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_api_server()
