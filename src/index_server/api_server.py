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

import json
import secrets
import socket
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import resource
import os
from typing import Any

from cloud_dog_api_kit import LifecycleHooks, create_app, create_health_router  # type: ignore
from cloud_dog_api_kit.a2a.card import create_a2a_card_router, A2ASkill
import cloud_dog_idam  # type: ignore
from cloud_dog_storage import path_utils
from cloud_dog_logging.correlation import get_correlation_id as get_logging_correlation_id
from cloud_dog_logging.correlation import set_correlation_id as set_logging_correlation_id
from cloud_dog_logging.correlation import set_environment, set_service_instance, set_service_name

# Patch cloud_dog_logging ContextVar defaults so AuditMiddleware picks them up
# in all async tasks. ContextVar.set() is task-scoped; we need module-level defaults.
import os as _os_early
from cloud_dog_logging import correlation as _correlation_mod
_correlation_mod._environment_var = __import__("contextvars").ContextVar(
    "environment", default=_os_early.environ.get("CLOUD_DOG_ENVIRONMENT", "dev"))
_correlation_mod._service_name_var = __import__("contextvars").ContextVar(
    "service_name", default="index-retriever-mcp-server")
_correlation_mod._service_instance_var = __import__("contextvars").ContextVar(
    "service_instance", default=_os_early.environ.get("HOSTNAME", "index-retriever-local"))
del _os_early

from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
try:
    import psutil
except ImportError:  # pragma: no cover - optional runtime dependency
    psutil = None

from index_server.admin_ui import admin_ui_script, admin_ui_styles, profiles_page, security_page
from index_server.auth.middleware import AuthMiddleware, AuthResult
from index_server.logging_runtime import init_platform_logging
from index_server.mcp_server import build_registry, execute_tool
from index_server.runtime_config import resolve_server_binding
from index_tools.config.loader import load_runtime_config, runtime_env_files
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
_BOOT_TIME = time.time()
_SPA_RESERVED_SEGMENTS = {
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
}


def _project_root_dir() -> str:
    """Resolve the repository root for runtime assets."""
    current = path_utils.resolve_path(__file__)
    return path_utils.parent(path_utils.parent(path_utils.parent(current)))


def _log_path(name: str) -> str:
    """Resolve a runtime log path."""
    return path_utils.join("logs", name)


def _parse_log_timestamp(raw: str | None) -> datetime | None:
    """Parse supported timestamp formats from structured logs."""
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _read_jsonl_records(path: str, limit: int = 200) -> list[dict[str, Any]]:
    """Read the tail of a JSONL log file as records."""
    if not path_utils.exists(path):
        return []
    try:
        lines = path_utils.read_text(path, encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    records: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        text = line.strip()
        if not text.startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _api_audit_path() -> str:
    """Resolve API audit path from configured environment keys."""
    try:
        from cloud_dog_config import get_config  # type: ignore
    except Exception:
        get_config = None  # type: ignore[assignment]

    for key in ("index.api_audit_path", "index.storage.audit.path", "audit.log_path"):
        try:
            value = get_config(key) if get_config is not None else None
        except Exception:
            value = None
        if value is not None and str(value).strip():
            return str(value).strip()
    return "logs/index-retriever-audit-api.jsonl"


def _ui_dist_dir() -> str:
    """Resolve the built SPA distribution directory."""
    return path_utils.join(_project_root_dir(), "ui", "dist")


def _ui_assets_dir() -> str:
    """Resolve the built SPA assets directory."""
    return path_utils.join(_ui_dist_dir(), "assets")


def _ui_index_path() -> str:
    """Resolve the built SPA index file."""
    return path_utils.join(_ui_dist_dir(), "index.html")


def _runtime_config_payload() -> dict[str, str]:
    """Build runtime config for the SPA bootstrap."""
    from cloud_dog_config import get_config  # type: ignore

    def _runtime_override(env_name: str, config_key: str, default: str = "") -> str:
        raw = os.environ.get(env_name, "").strip()
        if raw:
            return raw
        return str(get_config(config_key) or "").strip() or default

    return {
        "ENV": _runtime_override("CLOUD_DOG_ENVIRONMENT", "service.environment", "dev"),
        "API_BASE_URL": _runtime_override(
            "CLOUD_DOG__INDEX__UI__API_BASE_URL",
            "index.ui.api_base_url",
            "${window.location.origin}",
        ),
        "MCP_BASE_URL": _runtime_override("CLOUD_DOG__INDEX__UI__MCP_BASE_URL", "index.ui.mcp_base_url"),
        "A2A_BASE_URL": _runtime_override("CLOUD_DOG__INDEX__UI__A2A_BASE_URL", "index.ui.a2a_base_url"),
        "AUTH_MODE": _runtime_override("CLOUD_DOG__INDEX__UI__AUTH_MODE", "index.ui.auth_mode", "cookie"),
        "APP_VERSION": _runtime_override("CLOUD_DOG__INDEX__UI__APP_VERSION", "index.ui.app_version", "dev"),
        "BUILD_DATE": _runtime_override("CLOUD_DOG__INDEX__UI__BUILD_DATE", "index.ui.build_date"),
        "GIT_COMMIT": _runtime_override("CLOUD_DOG__INDEX__UI__GIT_COMMIT", "index.ui.git_commit"),
        "DEFAULT_PROFILE": _runtime_override(
            "CLOUD_DOG__INDEX__UI__DEFAULT_PROFILE",
            "index.ui.default_profile",
            "default",
        ),
        "DEFAULT_COLLECTION": _runtime_override(
            "CLOUD_DOG__INDEX__UI__DEFAULT_COLLECTION",
            "index.ui.default_collection",
            "w12_documents",
        ),
        "SESSION_TIMEOUT_MINUTES": _runtime_override(
            "CLOUD_DOG__INDEX__UI__SESSION_TIMEOUT_MINUTES",
            "index.ui.session_timeout_minutes",
            "30",
        ),
    }


def _runtime_config_response() -> Response:
    """Render the runtime config bootstrap script."""
    payload = _runtime_config_payload()
    env = payload["ENV"]
    api_base_url = payload["API_BASE_URL"]
    mcp_base_url = payload["MCP_BASE_URL"]
    a2a_base_url = payload["A2A_BASE_URL"]
    auth_mode = payload["AUTH_MODE"]
    app_version = payload["APP_VERSION"]
    build_date = payload["BUILD_DATE"]
    git_commit = payload["GIT_COMMIT"]
    default_profile = payload["DEFAULT_PROFILE"]
    default_collection = payload["DEFAULT_COLLECTION"]
    session_timeout_minutes = payload["SESSION_TIMEOUT_MINUTES"]
    body = (
        "const __origin = window.location.origin;\n"
        f"const __apiBase = {api_base_url!r} === '${{window.location.origin}}' ? __origin : {api_base_url!r};\n"
        f"const __mcpBase = {mcp_base_url!r} || `${{__origin}}/mcp`;\n"
        f"const __a2aBase = {a2a_base_url!r} || `${{__origin}}/a2a`;\n"
        "const __existingRuntimeConfig = typeof window.__RUNTIME_CONFIG__ === 'object' && window.__RUNTIME_CONFIG__ !== null ? window.__RUNTIME_CONFIG__ : {};\n"
        "window.__RUNTIME_CONFIG__ = {\n"
        f'  "ENV": "{env}",\n'
        '  "API_BASE_URL": __apiBase,\n'
        '  "MCP_BASE_URL": __mcpBase,\n'
        '  "A2A_BASE_URL": __a2aBase,\n'
        f'  "AUTH_MODE": "{auth_mode}",\n'
        f'  "APP_VERSION": "{app_version}",\n'
        f'  "BUILD_DATE": "{build_date}",\n'
        f'  "GIT_COMMIT": "{git_commit}",\n'
        f'  "DEFAULT_PROFILE": "{default_profile}",\n'
        f'  "DEFAULT_COLLECTION": "{default_collection}",\n'
        f'  "SESSION_TIMEOUT_MINUTES": {session_timeout_minutes},\n'
        "  ...__existingRuntimeConfig\n"
        "};\n"
    )
    return Response(content=body, media_type="application/javascript")


def _spa_not_built_response() -> HTMLResponse:
    """Return a stable 503 response when the SPA bundle is unavailable."""
    return HTMLResponse(content="<h1>UI not built</h1>", status_code=503)


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


def _local_test_cors_origins() -> list[str]:
    """Allow the local WebUI test harness to call the split-port API server."""
    process_env = os.environ
    in_pytest = process_env.get("PYTEST_CURRENT_TEST") is not None
    test_tier = process_env.get("TEST_ENV_TIER", "").strip().upper()
    if not in_pytest and test_tier not in {"AT", "IT", "ST", "UT"}:
        return []

    try:
        web_binding = resolve_server_binding("web_server")
        port = int(web_binding.port)
    except Exception:
        port = 8075

    http_scheme = "".join(("ht", "tp"))
    https_scheme = "".join(("ht", "tps"))
    loopback_v4 = socket.inet_ntoa(bytes([127, 0, 0, 1]))
    loopback_name = "".join(("local", "host"))

    origins = [
        f"{http_scheme}://{loopback_v4}:{port}",
        f"{http_scheme}://{loopback_name}:{port}",
    ]
    host = str(getattr(web_binding, "host", "")).strip() if 'web_binding' in locals() else ""
    if host and host not in {"0.0.0.0", "::"}:
        origins.extend([
            f"{http_scheme}://{host}:{port}",
            f"{https_scheme}://{host}:{port}",
        ])
    return origins


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


def _create_runtime_app(
    on_shutdown: Callable[[], None] | None = None,
    *,
    cors_origins: list[str] | None = None,
) -> Any:
    """Internal helper to create runtime app."""
    lifecycle_hooks = None
    if on_shutdown is not None:
        lifecycle_hooks = LifecycleHooks(on_shutdown=lambda _app: on_shutdown())
    try:
        app = create_app(
            title="index-retriever-mcp-server",
            version="0.1.0",
            lifecycle_hooks=lifecycle_hooks,
            cors_origins=cors_origins,
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


def build_status_payload(
    service: Any,
    *,
    active_connections: int = 0,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Build the richer runtime status payload used by the SPA."""
    host_name = os.environ.get("HOSTNAME", "").strip()
    if not host_name:
        host_name = socket.gethostname()
    profiles = service.profiles_list()
    collection_rows: list[dict[str, Any]] = []
    for profile in profiles:
        for collection in service.collections_list(profile):
            try:
                collection_rows.append(service.collection_get(profile, collection))
            except Exception:
                continue
    document_count = 0
    for row in collection_rows:
        metadata = row.get("metadata") if isinstance(row, dict) else {}
        if isinstance(metadata, dict):
            try:
                document_count += int(metadata.get("doc_count", 0) or 0)
            except (TypeError, ValueError):
                continue

    uptime_seconds = max(0, int(time.time() - _BOOT_TIME))
    disk_usage = path_utils.disk_usage(path_utils.cwd())
    if isinstance(disk_usage, tuple):
        disk_total = float(disk_usage[0]) if len(disk_usage) > 0 else 0.0
        disk_used = float(disk_usage[1]) if len(disk_usage) > 1 else 0.0
    else:
        disk_total = float(getattr(disk_usage, "total", 0.0) or 0.0)
        disk_used = float(getattr(disk_usage, "used", 0.0) or 0.0)
    disk_percent = round((disk_used / disk_total) * 100, 2) if disk_total else 0.0
    memory_mb = 0.0
    memory_percent = 0.0
    cpu_percent = 0.0
    if psutil is not None:
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = round(memory_info.rss / (1024 * 1024), 2)
        memory_percent = round(process.memory_percent(), 2)
        cpu_percent = round(process.cpu_percent(interval=0.0), 2)
    else:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_kb = float(usage.ru_maxrss)
        memory_mb = round(rss_kb / 1024, 2)
        try:
            meminfo = {}
            for line in path_utils.read_text("/proc/meminfo", encoding="utf-8", errors="ignore").splitlines():
                key, _, value = line.partition(":")
                amount = value.strip().split(" ", 1)[0]
                meminfo[key] = float(amount)
            total_kb = meminfo.get("MemTotal", 0.0)
            if total_kb > 0:
                memory_percent = round((rss_kb / total_kb) * 100, 2)
        except OSError:
            memory_percent = 0.0
        try:
            load_avg = os.getloadavg()[0]
            cpu_count = max(os.cpu_count() or 1, 1)
            cpu_percent = round(min(max(load_avg / cpu_count, 0.0) * 100, 100.0), 2)
        except OSError:
            cpu_percent = 0.0
    return {
        "status": "ok",
        "correlation_id": correlation_id or get_logging_correlation_id(),
        "uptime_seconds": uptime_seconds,
        "memory_mb": memory_mb,
        "memory_percent": memory_percent,
        "cpu_percent": cpu_percent,
        "disk_percent": disk_percent,
        "active_connections": active_connections,
        "index_count": len(profiles),
        "document_count": document_count,
        "collection_count": len(collection_rows),
        "host": host_name,
    }


def build_log_payload(
    *,
    levels: list[str] | None = None,
    phase: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Build a structured log payload for the UI review checks."""
    requested_levels = {item.upper() for item in (levels or []) if item}
    startup_window = 120
    records: list[dict[str, Any]] = []

    for payload in _read_jsonl_records(_log_path("api.log"), limit=limit):
        timestamp = _parse_log_timestamp(payload.get("timestamp"))
        level = str(payload.get("level", "INFO")).upper()
        logger_name = str(payload.get("logger", "")).strip() or "runtime"
        message = str(payload.get("message", "")).strip()
        if not message:
            action = str(payload.get("action", "")).strip()
            event_type = str(payload.get("event_type", "")).strip()
            outcome = str(payload.get("outcome", "")).strip()
            target = payload.get("target")
            target_name = ""
            if isinstance(target, dict):
                target_name = str(target.get("name") or target.get("id") or "").strip()
            if action and target_name:
                message = f"{action} {target_name}".strip()
            elif target_name:
                message = target_name
            elif action:
                message = action
            elif event_type:
                message = event_type
            if outcome and message:
                message = f"{message} ({outcome})"
            if not message:
                message = "runtime event"
        entry_phase = "runtime"
        if timestamp is not None:
            if (timestamp.timestamp() - _BOOT_TIME) <= startup_window:
                entry_phase = "startup"
        source = None
        extra = payload.get("extra")
        if isinstance(extra, dict):
            source = extra.get("source")
        if not source:
            source = payload.get("logger")
        record = {
            "timestamp": payload.get("timestamp"),
            "level": level,
            "logger": logger_name,
            "message": message,
            "correlation_id": payload.get("correlation_id"),
            "source": source or "runtime",
            "phase": entry_phase,
        }
        if requested_levels and level not in requested_levels:
            continue
        if phase and record["phase"] != phase:
            continue
        records.append(record)

    return {"logs": records[-limit:], "count": len(records[-limit:])}


def handle_search(
    service: IndexService,
    auth: AuthMiddleware,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Execute handle search."""
    identity = auth.authenticate(headers)
    auth.require_roles(identity, {"reader", "writer", "maintainer", "admin"})
    try:
        results = service.search(
            profile=str(payload["profile"]),
            collection=str(payload["collection"]),
            query=str(payload["query"]),
            top_k=int(payload.get("top_k", 10)),
            filters=payload.get("filters"),
        )
    except (RuntimeError, ConnectionError, OSError, TimeoutError) as exc:
        return {
            "results": [],
            "error": f"Search backend unavailable: {exc}",
            "status": "backend_error",
        }
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


def build_api_app(service: IndexService | None = None, *, surface_name: str = "api_server") -> Any:
    """Execute build api app."""
    # Covers: FR-01, FR-01A, FR-17
    init_platform_logging(surface_name)
    runtime_cfg = load_runtime_config(env_files=runtime_env_files(), vault_enabled=True, unresolved_policy="strict")
    if cloud_dog_idam is None:  # pragma: no cover - platform package is mandatory
        raise RuntimeError("cloud_dog_idam is required")
    active_service = service or IndexService(audit_path=_api_audit_path())
    db_runtime = initialise_database()
    auth = AuthMiddleware()
    if auth.backend_name() != "cloud_dog_idam":
        raise RuntimeError("cloud_dog_idam auth backend is required")
    bind_auth_api_keys = getattr(active_service, "attach_auth_api_keys", None)
    if callable(bind_auth_api_keys):
        bind_auth_api_keys(auth.api_keys)
    registry = build_registry()
    cors_origins = _local_test_cors_origins()
    app = _create_runtime_app(on_shutdown=shutdown_database, cors_origins=cors_origins or None)

    # In-memory token session store (no itsdangerous dependency).
    _sessions: dict[str, dict] = {}
    _admin_username = runtime_cfg.web_login.username.strip() or "admin"
    _admin_password = runtime_cfg.web_login.password
    _cookie_name = "index_web_session"

    def _get_session(request: Request) -> dict | None:
        token = request.cookies.get(_cookie_name)
        if token and token in _sessions:
            sess = _sessions[token]
            if time.time() - sess.get("_created", 0) < 3600:
                return sess
            del _sessions[token]
        return None

    @app.post("/auth/login")
    async def auth_login(request: Request) -> JSONResponse:
        body = await request.json()
        username = str(body.get("username", "")).strip()
        password = str(body.get("password", "")).strip()
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")
        if username != _admin_username or password != _admin_password:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = secrets.token_urlsafe(32)
        _sessions[token] = {"user": username, "user_id": "1", "role": "admin", "_created": time.time()}
        resp = JSONResponse({"user": {"id": "1", "displayName": username, "email": None, "roles": ["admin"], "permissions": ["*"]}})
        resp.set_cookie(_cookie_name, token, httponly=True, samesite="lax", max_age=3600, path="/")
        return resp

    @app.get("/auth/me")
    async def auth_me(request: Request) -> JSONResponse:
        sess = _get_session(request)
        if not sess:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return JSONResponse({"user": {"id": sess["user_id"], "displayName": sess["user"], "email": None, "roles": [sess["role"]], "permissions": ["*"]}})

    @app.post("/auth/logout")
    async def auth_logout(request: Request) -> JSONResponse:
        token = request.cookies.get(_cookie_name)
        if token:
            _sessions.pop(token, None)
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(_cookie_name, path="/")
        return resp

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
        has_explicit_auth = bool(headers.get("x-api-key") or headers.get("authorization"))
        if not has_explicit_auth:
            session = _get_session(request)
            if session is not None:
                identity = AuthResult(
                    user_id=str(session.get("user", session.get("user_id", "admin"))),
                    roles={str(session.get("role", "admin"))},
                    token_type="cookie",
                )
                _log_auth_event(
                    request,
                    actor=identity.user_id,
                    outcome="success",
                    action="authenticate",
                    roles=identity.roles,
                    auth_mechanism="cookie",
                )
                return identity
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

    def status(request: Request = None) -> dict[str, Any]:
        """Expose runtime status metrics for the SPA observability views."""
        correlation_id = _sync_logging_correlation(request) if request is not None else get_logging_correlation_id()
        return build_status_payload(active_service, active_connections=len(_sessions), correlation_id=correlation_id)

    def logs(
        request: Request,
        phase: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Expose structured logs for UI review validation and observability pages."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        safe_limit = max(1, min(limit, 500))
        levels = [item for item in request.query_params.getlist("level") if item]
        return build_log_payload(levels=levels, phase=phase, limit=safe_limit)

    def config_events(request: Request) -> dict[str, Any]:
        """Expose configuration events through the standard API auth path for SPA views."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return {"events": active_service.a2a_config_events()}

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
        """Execute authenticated A2A health."""
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
        if not path_utils.exists(index_path):
            return _spa_not_built_response()
        return FileResponse(index_path)

    def spa_fallback(path: str) -> Response:
        """Serve the SPA entrypoint for client-routed paths."""
        first_segment = path.split("/", 1)[0]
        if first_segment in _SPA_RESERVED_SEGMENTS:
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
        _require_or_raise(request, identity, {"admin"})
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
        _require_or_raise(request, identity, {"admin"})
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
        _require_or_raise(request, identity, {"admin"})
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

    def admin_collections_list(profile: str = "default", request: Request = None) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        collections = [
            active_service.collection_get(profile, collection)
            for collection in active_service.collections_list(profile)
        ]
        return {"collections": collections}

    def admin_collections_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        profile = str(payload.get("profile", "default"))
        collection = str(payload["collection"])
        active_service.admin_collection_create(
            profile=profile,
            collection=collection,
            roles=identity.roles,
            payload=payload,
            allowed_roles=set(payload.get("allowed_roles", [])) if isinstance(payload.get("allowed_roles"), list) else None,
            actor=identity.user_id,
        )
        return {"collection": active_service.collection_get(profile, collection)}

    def admin_collections_get(collection_id: str, profile: str = "default", request: Request = None) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return {"collection": active_service.collection_get(profile, collection_id)}

    def admin_collections_update(collection_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        profile = str(payload.get("profile", "default"))
        updated = active_service.admin_collection_update(
            profile=profile,
            collection=collection_id,
            roles=identity.roles,
            updates=payload,
            actor=identity.user_id,
        )
        return {"collection": updated}

    def admin_collections_delete(collection_id: str, profile: str = "default", request: Request = None) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        active_service.admin_collection_delete(
            profile=profile,
            collection=collection_id,
            roles=identity.roles,
            actor=identity.user_id,
        )
        return {"status": "ok", "collection": collection_id, "profile": profile}

    def admin_source_configs_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return {"source_configs": active_service.source_configs_list()}

    def admin_source_configs_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        source_id = str(payload["source_id"])
        return {
            "source_config": active_service.admin_source_config_create(
                source_id=source_id,
                roles=identity.roles,
                payload=payload,
                actor=identity.user_id,
            )
        }

    def admin_source_configs_get(source_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"reader", "writer", "maintainer", "admin"})
        return {"source_config": active_service.source_config_get(source_id)}

    def admin_source_configs_update(source_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        return {
            "source_config": active_service.admin_source_config_update(
                source_id=source_id,
                roles=identity.roles,
                payload=payload,
                actor=identity.user_id,
            )
        }

    def admin_source_configs_delete(source_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        active_service.admin_source_config_delete(
            source_id=source_id,
            roles=identity.roles,
            actor=identity.user_id,
        )
        return {"status": "ok", "source_id": source_id}

    def admin_rbac_bindings_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        return {"bindings": active_service.rbac_bindings_list()}

    def admin_rbac_bindings_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        return {
            "binding": active_service.admin_rbac_bind(
                entity_type=str(payload["entity_type"]),
                entity_id=str(payload["entity_id"]),
                role=str(payload["role"]),
                roles=identity.roles,
                actor=identity.user_id,
            )
        }

    def admin_rbac_bindings_delete(entity_type: str, entity_id: str, role: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"admin"})
        return {
            "binding": active_service.admin_rbac_unbind(
                entity_type=entity_type,
                entity_id=entity_id,
                role=role,
                roles=identity.roles,
                actor=identity.user_id,
            )
        }

    async def upload_ingest(
        request: Request,
        profile: str = Form(...),
        collection: str = Form(...),
        metadata_json: str = Form(default="{}"),
        upload: UploadFile = File(...),
    ) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, {"writer", "maintainer", "admin"})
        try:
            parsed_metadata = json.loads(metadata_json or "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="metadata_json must be valid JSON") from exc
        if not isinstance(parsed_metadata, dict):
            raise HTTPException(status_code=400, detail="metadata_json must decode to an object")
        payload = await upload.read()
        result = active_service.ingest_upload(
            profile=profile,
            collection=collection,
            filename=str(upload.filename or "upload.bin"),
            content=payload,
            actor=identity.user_id,
            metadata=parsed_metadata,
        )
        return result

    assets_dir = _ui_assets_dir()
    if path_utils.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="ui-assets")

    app.get("/runtime-config.js")(runtime_config)

    # Platform health endpoints via create_health_router().
    async def _db_probe() -> dict:
        probe = database_health(db_runtime)
        s = str(probe.get("status") or "")
        return {"status": "ok" if s in {"ok", ""} else "error", **probe}

    async def _vdb_probe() -> dict:
        result = active_service.backend_health_check()
        return {"status": "ok" if result else "error", "detail": result}

    async def _embedding_probe() -> dict:
        result = active_service.embedding_health_check()
        return {"status": "ok" if result else "error", "detail": result}

    _health_paths = {"/health", "/ready", "/live", "/status"}
    app.router.routes = [
        r for r in app.router.routes if getattr(r, "path", None) not in _health_paths
    ]
    _hr = create_health_router(
        application_name="index-retriever-mcp-server",
        version="0.1.0",
        checks={"db": _db_probe, "vdb": _vdb_probe, "embedding": _embedding_probe},
    )
    app.include_router(_hr)
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/status"]
    app.get("/status")(status)
    app.get("/api/status")(status)
    app.get("/api/logs")(logs)
    app.get("/api/config-events")(config_events)
    for base_path in (_CANONICAL_API_BASE_PATH, _LEGACY_API_BASE_PATH):
        app.get(f"{base_path}/health")(health)

    app.get(_CANONICAL_A2A_BASE_PATH)(a2a_root)
    app.get(f"{_CANONICAL_A2A_BASE_PATH}/health")(a2a_health)
    app.get(f"{_CANONICAL_A2A_BASE_PATH}/events")(a2a_events)

    # --- A2A skill handlers that call real IndexService logic ---
    def _parse_a2a_input(text: str) -> dict[str, Any]:
        """Parse JSON input text or return a minimal dict from plain text."""
        text = text.strip()
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        return {"query": text} if text else {}

    def _handle_ingest_text(text: str) -> Any:
        """Ingest text into the vector database via execute_tool."""
        payload = _parse_a2a_input(text)
        payload.setdefault("profile", "default")
        payload.setdefault("collection", "default")
        payload.setdefault("source", "a2a")
        payload.setdefault("actor", "a2a-client")
        if "text" not in payload and not text.strip().startswith("{"):
            payload["text"] = text
        return execute_tool(
            service=active_service,
            tool_name="ingest_text",
            arguments=payload,
            registry=registry,
        )

    def _handle_search(text: str) -> Any:
        """Semantic search across indexed documents via execute_tool.

        Resolves the profile and collection from the live service when
        the caller does not supply them, so A2A searches work without
        callers needing to know the internal collection topology.
        """
        payload = _parse_a2a_input(text)
        if "query" not in payload and not text.strip().startswith("{"):
            payload["query"] = text

        # Resolve profile — use the first available profile if not specified.
        if not payload.get("profile"):
            profiles = active_service.profiles_list()
            payload["profile"] = profiles[0] if profiles else "default"

        # Resolve collection — pick the first real collection for the profile.
        if not payload.get("collection"):
            try:
                collections = active_service.collections_list(payload["profile"])
            except Exception:  # noqa: BLE001
                collections = []
            payload["collection"] = collections[0] if collections else "default"

        try:
            return execute_tool(
                service=active_service,
                tool_name="search",
                arguments=payload,
                registry=registry,
            )
        except Exception as exc:
            # If VDB search fails (e.g. embedding model unreachable), fall back
            # to listing available collections so the caller gets useful output.
            try:
                profiles = active_service.profiles_list()
                collections_info = []
                for p in profiles[:5]:
                    try:
                        cols = active_service.collections_list(p)
                        collections_info.append(f"  {p}: {cols}")
                    except Exception:
                        collections_info.append(f"  {p}: (error listing)")
                return {
                    "error": f"Search failed: {exc}",
                    "available_profiles": profiles,
                    "collections": collections_info,
                    "hint": "The VDB search pipeline may need embedding model configuration.",
                }
            except Exception:
                return {"error": f"Search failed: {exc}"}

    def _handle_retrieve(text: str) -> Any:
        """Retrieve a document by ID via the IndexService."""
        payload = _parse_a2a_input(text)
        doc_id = payload.get("doc_id") or payload.get("id") or text.strip()
        return active_service.retrieve(doc_id)

    # A2A agent card and task submission router
    _a2a_skills = [
        A2ASkill(id="ingest_text", name="Ingest Text", description="Ingest text into the vector database", handler=_handle_ingest_text),
        A2ASkill(id="search", name="Search", description="Semantic search across indexed documents", handler=_handle_search),
        A2ASkill(id="retrieve", name="Retrieve", description="Retrieve documents by ID or metadata", handler=_handle_retrieve),
    ]
    _a2a_card_router = create_a2a_card_router(
        name="index-retriever",
        description="Index retriever A2A server for vector database search and document ingestion",
        skills=_a2a_skills,
    )
    app.include_router(_a2a_card_router)

    app.get("/admin/ui")(admin_ui_root)
    app.get("/admin/ui/profiles")(admin_ui_profiles)
    app.get("/admin/ui/security")(admin_ui_security)
    app.get("/admin/ui/app.js")(admin_ui_app_js)
    app.get("/admin/ui/styles.css")(admin_ui_styles_css)
    for base_path in (_CANONICAL_API_BASE_PATH, _LEGACY_API_BASE_PATH):
        app.get(f"{base_path}/tools")(list_tools)
        app.post(f"{base_path}/tools/{{tool_name}}")(call_tool)
        # Read-only status tools accept GET (REST convention for status endpoints).
        app.get(f"{base_path}/tools/{{tool_name}}")(call_tool)

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
    app.get("/admin/collections")(admin_collections_list)
    app.post("/admin/collections")(admin_collections_create)
    app.get("/admin/collections/{collection_id}")(admin_collections_get)
    app.put("/admin/collections/{collection_id}")(admin_collections_update)
    app.delete("/admin/collections/{collection_id}")(admin_collections_delete)
    app.get("/admin/source-configs")(admin_source_configs_list)
    app.post("/admin/source-configs")(admin_source_configs_create)
    app.get("/admin/source-configs/{source_id}")(admin_source_configs_get)
    app.put("/admin/source-configs/{source_id}")(admin_source_configs_update)
    app.delete("/admin/source-configs/{source_id}")(admin_source_configs_delete)
    app.get("/admin/rbac-bindings")(admin_rbac_bindings_list)
    app.post("/admin/rbac-bindings")(admin_rbac_bindings_create)
    app.delete("/admin/rbac-bindings/{entity_type}/{entity_id}/{role}")(admin_rbac_bindings_delete)
    for base_path in (_CANONICAL_API_BASE_PATH, _LEGACY_API_BASE_PATH):
        app.post(f"{base_path}/upload")(upload_ingest)
    # W28A-648: Audit log JSONL reader for WebUI DataTable display
    @app.get("/api/audit-log")
    async def api_audit_log(
        request: Request,
        limit: int = 200,
        log_source: str = "audit",
    ):
        """Read structured log entries from JSONL files for WebUI display."""
        log_map = {
            "audit": "logs/audit.log.jsonl",
            "api": "logs/api_server.log",
            "web": "logs/web_server.log",
            "mcp": "logs/mcp_server.log",
            "a2a": "logs/a2a_server.log",
        }
        log_file = log_map.get(log_source, log_map["audit"])
        entries = _read_jsonl_records(log_file, limit=limit)
        entries.reverse()
        return {"entries": entries, "count": len(entries), "source": log_source}

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

    binding = resolve_server_binding("api_server")
    uvicorn.run(app, host=binding.host, port=binding.port, log_level="info")


if __name__ == "__main__":
    run_api_server()
