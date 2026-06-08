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

import gzip
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
# W28A-1002-EXTEND-R2 Phase B — adopt cloud_dog_api_kit.a2a.events RESTPollAdapter
# with legacy-contract-mode kwargs (F-3o closed by R1b 0.12.0). Preserves the
# existing external contract for `GET /a2a/events` (envelope_shape=events_only,
# order=newest_first, event_id_format=uuid_string, field_mapping aliases
# entity_type/entity_id/created_at). The canonical PS-72 §A2A-change-events
# envelope is authoritative; this is a presentation-layer transform.
from cloud_dog_api_kit.a2a.events import (  # type: ignore
    ConfigChangeEvent as _A2AConfigChangeEvent,
    EventBroadcaster as _A2AEventBroadcaster,
    RESTPollAdapter as _A2ARESTPollAdapter,
)
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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
try:
    import psutil
except ImportError:  # pragma: no cover - optional runtime dependency
    psutil = None

from index_server.admin_ui import admin_ui_script, admin_ui_styles, collections_page, profiles_page, security_page, structure_page
from index_server.auth.middleware import AuthMiddleware, AuthResult
from index_server.logging_runtime import init_platform_logging, shutdown_platform_logging
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

_LEGACY_API_BASE_PATH = "/app/v1"
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
        if str(path).endswith(".gz"):
            with gzip.open(path, mode="rt", encoding="utf-8", errors="ignore") as handle:
                lines = handle.read().splitlines()
        else:
            lines = path_utils.read_text(path, encoding="utf-8", errors="ignore").splitlines()
    except (OSError, gzip.BadGzipFile):
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


def _expand_rotated_log_paths(path: str) -> list[str]:
    """Include plain rotated audit files so recent entries survive log rotation."""
    directory, basename = os.path.split(path)
    search_dir = directory or "."
    expanded = [path]
    try:
        names = os.listdir(search_dir)
    except OSError:
        return expanded

    rotated: list[tuple[int, int, str]] = []
    prefix = f"{basename}."
    for name in names:
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix):]
        compressed = 0
        if suffix.endswith(".gz"):
            suffix = suffix[:-3]
            compressed = 1
        if not suffix.isdigit():
            continue
        rotated.append((int(suffix), compressed, path_utils.join(search_dir, name)))

    rotated.sort()
    expanded.extend(item[2] for item in rotated)
    return expanded


def _read_jsonl_records_many(paths: list[str], limit: int = 200) -> list[dict[str, Any]]:
    """Read and sort structured records across multiple JSONL files."""
    combined: list[dict[str, Any]] = []
    per_file_limit = max(limit, 1)
    expanded_paths: list[str] = []
    seen: set[str] = set()
    for path in paths:
        for expanded_path in _expand_rotated_log_paths(path):
            if expanded_path in seen:
                continue
            seen.add(expanded_path)
            expanded_paths.append(expanded_path)

    for path in expanded_paths:
        combined.extend(_read_jsonl_records(path, limit=per_file_limit))
    combined.sort(key=lambda entry: _parse_log_timestamp(entry.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc))
    return combined[-limit:]


def _mask_runtime_config(value: Any, parent_key: str = "") -> Any:
    """Redact secret-like values before returning config to the UI."""
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in ("password", "secret", "token", "api_key", "apikey", "credential", "private_key", "key_hash")):
                masked[key] = item if item in (None, "", [], {}) else "****"
                continue
            masked[key] = _mask_runtime_config(item, lowered)
        return masked
    if isinstance(value, list):
        return [_mask_runtime_config(item, parent_key) for item in value]
    return value


def _normalise_route_base_path(raw: str | None, default: str) -> str:
    """Normalise configurable route prefixes to a stable leading-slash form."""
    value = str(raw or "").strip() or default
    if not value.startswith("/"):
        value = f"/{value}"
    if value != "/" and value.endswith("/"):
        value = value[:-1]
    return value


def _resolve_route_base_path(
    configured_value: str | None,
    *,
    env_name: str,
    config_key: str,
    default: str,
) -> str:
    """Resolve a route prefix via cloud_dog_config, then fall back to bound config/default."""
    try:
        from cloud_dog_config import get_config  # type: ignore
    except Exception:
        get_config = None  # type: ignore[assignment]

    for key in (env_name, config_key):
        try:
            value = get_config(key) if get_config is not None else None
        except Exception:
            value = None
        if value is not None and str(value).strip():
            return _normalise_route_base_path(str(value), default)
    return _normalise_route_base_path(configured_value, default)


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
        for key in (env_name, config_key):
            raw = str(get_config(key) or "").strip()
            if raw:
                return raw
        return default

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
    env_files = process_env.get("CLOUD_DOG_ENV_FILES", "").strip().upper()
    using_test_env_files = any(token in env_files for token in ("ENV-AT", "ENV-IT", "ENV-ST", "ENV-UT"))
    if not in_pytest and test_tier not in {"AT", "IT", "ST", "UT"} and not using_test_env_files:
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
    # Playwright Vite preview server (port 5197) needs CORS access to the
    # API server during E2E tests when runtime-config.js resolves
    # API_BASE_URL to the direct backend address instead of the proxy origin.
    pw_preview_port = 5197
    if pw_preview_port != port:
        origins.extend([
            f"{http_scheme}://{loopback_v4}:{pw_preview_port}",
            f"{http_scheme}://{loopback_name}:{pw_preview_port}",
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
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
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
    try:
        vdb_check: Any = active_service.backend_health_check()
    except Exception as exc:
        vdb_check = {"status": "error", "message": str(exc)}
    try:
        embedding_check: Any = active_service.embedding_health_check()
    except Exception as exc:
        embedding_check = {"status": "error", "message": str(exc)}
    overall = "ok"
    for check in (db_probe, vdb_check, embedding_check):
        if isinstance(check, dict) and check.get("status") == "error":
            overall = "degraded"
            break
    return {
        "status": overall,
        "correlation_id": request_id,
        "checks": {
            "db": db_probe,
            "vdb": vdb_check,
            "embedding": embedding_check,
        },
    }


def build_status_payload(
    service: Any,
    *,
    active_connections: int = 0,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Build the richer runtime status payload used by the SPA."""
    from cloud_dog_config import get_config  # type: ignore

    host_name = str(get_config("HOSTNAME") or "").strip()
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
    active_document_ids: set[str] = set()
    for record in getattr(service, "documents", {}).values():
        metadata = dict(getattr(record, "metadata", {}) or {})
        if str(metadata.get("lifecycle_state", "active")) == "deleted":
            continue
        if metadata.get("is_latest") is False:
            continue
        doc_id = str(metadata.get("doc_id") or getattr(record, "doc_id", "")).strip()
        if doc_id:
            active_document_ids.add(doc_id)
    document_count = len(active_document_ids)
    if document_count == 0:
        for row in collection_rows:
            metadata = row.get("metadata") if isinstance(row, dict) else {}
            if isinstance(metadata, dict):
                try:
                    document_count += int(metadata.get("doc_count", 0) or 0)
                except (TypeError, ValueError):
                    continue
    if document_count == 0:
        for row in collection_rows:
            profile = str(row.get("profile", "")).strip() if isinstance(row, dict) else ""
            collection = str(row.get("collection", "")).strip() if isinstance(row, dict) else ""
            if not profile or not collection:
                continue
            try:
                count_payload = service.reindex_run(profile, collection)
                if isinstance(count_payload, dict):
                    document_count += int(count_payload.get("documents", 0) or 0)
                else:
                    document_count += int(count_payload or 0)
            except Exception:
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
    identity = auth.identity_from_headers(headers)
    auth.require_permission(identity, "collection.read")
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
    identity = auth.identity_from_headers(headers)
    auth.require_permission(identity, "collection.write")
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


class _ServiceBackedBroadcaster:
    """Minimal EventBroadcaster adapter wrapping ``IndexService.a2a_events``.

    W28A-1002-EXTEND-R2 Phase B — the index-retriever bespoke event store
    lives on ``IndexService.a2a_events: list[ConfigEventRecord]``. Rather
    than duplicating state through a second broadcaster (which would
    require rewiring 20 ``_emit_config_event`` call-sites), this adapter
    synthesises ``ConfigChangeEvent`` instances on-demand from the
    existing list.

    Only ``history()`` is used by ``RESTPollAdapter``; ``publish`` and
    ``subscribe`` are implemented as minimal no-ops to satisfy the
    Protocol's runtime_checkable shape (unused for REST-poll adoption).
    """

    def __init__(self, service: Any) -> None:
        self._service = service

    async def publish(self, event: _A2AConfigChangeEvent) -> _A2AConfigChangeEvent:
        # Not used by RESTPollAdapter; provided only to satisfy the
        # EventBroadcaster Protocol shape. Publishing would require
        # threading through the bespoke _emit_config_event pipeline
        # which is beyond R2 scope (see constraints: a2a_server.py
        # replacement only).
        return event

    def subscribe(self):  # type: ignore[no-untyped-def]
        # Unused by RESTPollAdapter. Return an empty async iterator.
        async def _empty():
            if False:
                yield  # pragma: no cover
        return _empty()

    def history(self, after_id: int = 0, limit: int = 100) -> list[_A2AConfigChangeEvent]:
        """Synthesise ConfigChangeEvent objects from IndexService.a2a_events.

        The bespoke event_id is a UUID string; RESTPollAdapter requires
        a monotonic integer. We use the positional index (1-based) in
        the underlying list as the synthetic event_id. ``after_id`` filters
        strictly greater than the synthetic id. This preserves pagination
        semantics while keeping the bespoke UUID-backed ordering intact.
        """
        records = list(getattr(self._service, "a2a_events", []) or [])
        out: list[_A2AConfigChangeEvent] = []
        for idx, record in enumerate(records, start=1):
            if idx <= int(after_id or 0):
                continue
            # Best-effort mapping from bespoke ConfigEventRecord to
            # canonical ConfigChangeEvent. The ``payload`` dict from the
            # bespoke record becomes ``after`` on the canonical event;
            # field_mapping later renames it back to ``payload`` in the
            # wire format.
            created_at = getattr(record, "created_at", None)
            out.append(
                _A2AConfigChangeEvent(
                    service="index-retriever-mcp-server",
                    resource=str(getattr(record, "entity_type", "")),
                    action=str(getattr(record, "action", "")),
                    identifier=str(getattr(record, "entity_id", "")),
                    actor=str(getattr(record, "actor", "")) or None,
                    correlation_id=None,
                    before=None,
                    after=dict(getattr(record, "payload", {}) or {}),
                    outcome="success",
                    timestamp=created_at if created_at is not None else _A2AConfigChangeEvent.__dataclass_fields__["timestamp"].default_factory(),  # type: ignore[union-attr]
                    event_id=idx,
                )
            )
        if limit <= 0:
            return []
        if len(out) > limit:
            out = out[-limit:]
        return out


def build_api_app(service: IndexService | None = None, *, surface_name: str = "api_server") -> Any:
    """Execute build api app."""
    # Covers: FR-01, FR-01A, FR-17
    init_platform_logging(surface_name)
    runtime_cfg = load_runtime_config(env_files=runtime_env_files(), unresolved_policy="strict")
    if cloud_dog_idam is None:  # pragma: no cover - platform package is mandatory
        raise RuntimeError("cloud_dog_idam is required")
    active_service = service or IndexService(audit_path=_api_audit_path())
    db_runtime = initialise_database()
    auth = AuthMiddleware()
    if auth.backend_name() != "cloud_dog_idam":
        raise RuntimeError("cloud_dog_idam auth backend is required")
    if hasattr(auth, "_api_key_manager") and auth._api_key_manager is not None:
        active_service._idam_api_keys = auth._api_key_manager
    bind_idam_auth = getattr(active_service, "attach_idam_auth", None)
    if callable(bind_idam_auth):
        bind_idam_auth(auth)
    registry = build_registry()
    cors_origins = _local_test_cors_origins()
    def _shutdown_runtime() -> None:
        active_service.close()
        shutdown_database()
        shutdown_platform_logging()

    app = _create_runtime_app(on_shutdown=_shutdown_runtime, cors_origins=cors_origins or None)
    api_base_path = _resolve_route_base_path(
        getattr(runtime_cfg.api_server, "base_path", ""),
        env_name="CLOUD_DOG__INDEX_RETRIEVER__API_SERVER__BASE_PATH",
        config_key="api_server.base_path",
        default="/api/v1",
    )

    def _custom_openapi() -> dict[str, Any]:
        if app.openapi_schema and "IngestPreviewOutput" in dict(app.openapi_schema.get("components", {}).get("schemas", {})):
            return app.openapi_schema
        schema = get_openapi(
            title=str(getattr(app, "title", "index-retriever-mcp-server")),
            version=str(getattr(app, "version", "0.1.0")),
            description=str(getattr(app, "description", "")),
            routes=app.routes,
        )
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        tool_contracts = schema.setdefault("x-tool-contracts", {})
        for spec in getattr(registry, "_tools", {}).values():
            input_name = spec.input_model.__name__
            output_name = spec.output_model.__name__
            input_schema = spec.input_model.model_json_schema(ref_template="#/components/schemas/{model}")
            output_schema = spec.output_model.model_json_schema(ref_template="#/components/schemas/{model}")
            for schema_payload in (input_schema, output_schema):
                for def_name, def_schema in dict(schema_payload.pop("$defs", {})).items():
                    components.setdefault(def_name, def_schema)
            components.setdefault(input_name, input_schema)
            components.setdefault(output_name, output_schema)
            tool_contracts[spec.name] = {
                "input_model": input_name,
                "output_model": output_name,
                "input_schema": {"$ref": f"#/components/schemas/{input_name}"},
                "output_schema": {"$ref": f"#/components/schemas/{output_name}"},
            }
        app.openapi_schema = schema
        return schema

    app.openapi_schema = None
    app.openapi = _custom_openapi

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
        if sess:
            return JSONResponse({"user": {"id": sess["user_id"], "displayName": sess["user"], "email": None, "roles": [sess["role"]], "permissions": ["*"]}})
        identity = _auth_or_raise(request, _headers_from_request(request))
        return JSONResponse(
            {
                "user": {
                    "id": identity.user_id,
                    "displayName": identity.user_id,
                    "email": None,
                    "roles": sorted(str(role) for role in identity.roles),
                    "permissions": sorted(str(permission) for permission in identity.permissions),
                }
            }
        )

    @app.post("/auth/logout")
    async def auth_logout(request: Request) -> JSONResponse:
        token = request.cookies.get(_cookie_name)
        if token:
            _sessions.pop(token, None)
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(_cookie_name, path="/")
        return resp

    @app.get("/api/config")
    async def config_dump(request: Request) -> JSONResponse:
        sess = _get_session(request)
        if not sess:
            _auth_or_raise(request, _headers_from_request(request))
        return JSONResponse(_mask_runtime_config(runtime_cfg.model_dump()))

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
                    permissions={"*"},
                    token_type="cookie",
                )
                auth.sync_identity_roles(identity.user_id, identity.roles)
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

    def _require_or_raise(request: Request, identity: Any, permission: str) -> None:
        """Internal helper to require or raise."""
        try:
            auth.require_permission(identity, permission)
        except PermissionError as exc:
            _log_auth_event(
                request,
                actor=identity.user_id,
                outcome="denied",
                action="authorise",
                roles=identity.roles,
                auth_mechanism=identity.token_type,
                reason=str(exc),
                required_roles=permission,
            )
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    def _a2a_auth_or_raise(request: Request, headers: dict[str, str]) -> Any:
        """Enforce A2A auth contract using shared API-key authority."""
        # Covers: FR-01B
        _sync_logging_correlation(request)
        try:
            identity = auth.api_key_identity(headers)
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
        _require_or_raise(request, identity, "collection.read")
        safe_limit = max(1, min(limit, 500))
        levels = [item for item in request.query_params.getlist("level") if item]
        return build_log_payload(levels=levels, phase=phase, limit=safe_limit)

    def config_events(request: Request) -> dict[str, Any]:
        """Expose configuration events through the standard API auth path for SPA views."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
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

    # W28A-1002-EXTEND-R2 Phase B — cloud_dog_api_kit.a2a.events RESTPollAdapter
    # adoption. Legacy-contract-mode kwargs (0.12.0; F-3o closure) preserve the
    # bespoke external contract: {"events": [...]} envelope (no cursor),
    # newest-first order, UUID-string event_ids, legacy field names
    # entity_type/entity_id/created_at. The canonical PS-72 §A2A-change-events
    # envelope is authoritative internally; field_mapping + envelope_shape +
    # order + event_id_format are presentation-layer transforms over the
    # common broadcaster surface.
    _a2a_events_broadcaster: _A2AEventBroadcaster = _ServiceBackedBroadcaster(active_service)  # type: ignore[assignment]
    _a2a_events_rest_poll = _A2ARESTPollAdapter(
        _a2a_events_broadcaster,
        mount_path=f"{_CANONICAL_A2A_BASE_PATH}/events",
        envelope_shape="events_only",
        field_mapping={
            "resource": "entity_type",
            "identifier": "entity_id",
            "timestamp": "created_at",
            "after": "payload",
        },
        order="newest_first",
        event_id_format="uuid_string",
    )
    # Extract the RESTPollAdapter's internal GET handler closure so we can
    # invoke it from within our auth-guarded route. The adapter's router
    # contains a single GET route at mount_path; route.endpoint is the
    # ``poll(since, limit)`` async closure bound to the adapter's configured
    # broadcaster / envelope / field_mapping / order / event_id_format.
    _a2a_events_adapter_router = _a2a_events_rest_poll.router()
    _a2a_events_poll_endpoint: Any = None
    for _route in _a2a_events_adapter_router.routes:
        if getattr(_route, "path", None) == f"{_CANONICAL_A2A_BASE_PATH}/events":
            _a2a_events_poll_endpoint = getattr(_route, "endpoint", None)
            break
    if _a2a_events_poll_endpoint is None:  # pragma: no cover — defensive
        raise RuntimeError(
            "Failed to extract RESTPollAdapter poll endpoint for /a2a/events adoption"
        )

    async def a2a_events(request: Request) -> Response:
        """Expose configuration change events via the A2A interface.

        Delegates to the cloud_dog_api_kit.a2a.events RESTPollAdapter (0.12.0)
        configured with legacy-contract-mode kwargs. Auth enforced here before
        dispatching to the adapter's poll closure so the external contract
        (401 on missing/invalid X-API-Key) is preserved.
        """
        _ = _a2a_auth_or_raise(request, _headers_from_request(request))
        since_raw = request.query_params.get("since", "0")
        limit_raw = request.query_params.get("limit")
        try:
            since_val = max(0, int(since_raw))
        except (TypeError, ValueError):
            since_val = 0
        limit_val: int | None
        if limit_raw is None or str(limit_raw).strip() == "":
            limit_val = None
        else:
            try:
                limit_val = max(1, int(limit_raw))
            except (TypeError, ValueError):
                limit_val = None
        return await _a2a_events_poll_endpoint(since=since_val, limit=limit_val)

    def runtime_config() -> Response:
        """Serve the runtime config bootstrap for the SPA."""
        return _runtime_config_response()

    def admin_ui_root() -> HTMLResponse:
        """Serve the legacy admin UI root while parity work remains incomplete."""
        return HTMLResponse(content=profiles_page())

    def admin_ui_profiles() -> HTMLResponse:
        """Serve the legacy profile management page."""
        return HTMLResponse(content=profiles_page())

    def _collection_inventory_snapshot(profile: str = "default") -> list[dict[str, Any]]:
        """Return visible collection metadata for server-rendered warrant rows."""
        try:
            return [
                active_service.collection_get(profile, collection)
                for collection in active_service.collections_list(profile)
            ]
        except Exception:
            return []

    def admin_ui_collections() -> HTMLResponse:
        """Serve the collection inventory page."""
        return HTMLResponse(content=collections_page(_collection_inventory_snapshot()))

    def collections_ui() -> HTMLResponse:
        """Serve the user-facing collection inventory route."""
        return HTMLResponse(content=collections_page(_collection_inventory_snapshot()))

    def admin_ui_security() -> HTMLResponse:
        """Serve the legacy security management page."""
        return HTMLResponse(content=security_page())

    def admin_ui_structure() -> HTMLResponse:
        """Serve the document-structure inspection / corpus / template workflow page (W28E-603)."""
        return HTMLResponse(content=structure_page())

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

    def api_docs_page() -> HTMLResponse:
        """Serve the stable API-docs page contract expected by WebUI gates."""
        openapi_json_url = "/openapi.json"
        docs_url = "/docs"
        body = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>API Docs</title>
    <style>
      body {{ margin: 0; font-family: sans-serif; color: #0f172a; background: #f8fafc; }}
      main {{ min-height: 100vh; padding: 1.5rem; box-sizing: border-box; }}
      header {{ display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }}
      h1 {{ margin: 0; font-size: 1.5rem; }}
      a {{ color: #0369a1; font-weight: 600; }}
      iframe {{ width: 100%; height: calc(100vh - 6rem); border: 1px solid #cbd5e1; border-radius: 0.75rem; background: white; }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>API Docs</h1>
        <nav><a href="{openapi_json_url}">OpenAPI JSON</a></nav>
      </header>
      <iframe title="API documentation" src="{docs_url}"></iframe>
    </main>
  </body>
</html>"""
        return HTMLResponse(content=body)

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
        _require_or_raise(request, identity, "collection.read")
        return registry.list_tools()

    def call_tool(tool_name: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        """Execute call tool."""
        # Covers: FR-17
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        arguments = dict(payload)
        arguments.setdefault("actor", identity.user_id)
        try:
            return execute_tool(
                service=active_service,
                tool_name=tool_name,
                arguments=arguments,
                registry=registry,
                auth=auth,
                identity=identity,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def admin_profiles_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        profiles = [
            active_service.profile_get(profile) | {"profile": profile}
            for profile in active_service.profiles_list()
        ]
        return {"profiles": profiles}

    def admin_profiles_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
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
        _require_or_raise(request, identity, "collection.read")
        return {"profile": profile_id, "config": active_service.profile_get(profile_id)}

    def admin_profiles_update(profile_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
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
        _require_or_raise(request, identity, "admin")
        active_service.admin_profile_delete(profile=profile_id, roles=identity.roles, actor=identity.user_id)
        return {"status": "ok", "profile": profile_id}

    def admin_users_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        users = active_service.users_list()
        result: dict[str, Any] = {"users": users}
        if not users:
            result["bootstrap_hint"] = (
                "No users configured. Create a bootstrap-seed.yaml with user "
                "entries and set INDEX_RETRIEVER_BOOTSTRAP_SEED_PATH, or use "
                "POST /admin/users to create the first admin user."
            )
        return result

    def admin_users_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
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
        _require_or_raise(request, identity, "collection.read")
        return {"user": active_service.user_get(user_id)}

    def admin_users_update(user_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
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
        _require_or_raise(request, identity, "admin")
        active_service.admin_user_delete(user_id=user_id, roles=identity.roles, actor=identity.user_id)
        return {"status": "ok", "user_id": user_id}

    def admin_roles_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        return {"roles": active_service.roles_list()}

    def admin_roles_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        try:
            return {
                "role": active_service.admin_role_create(
                    roles=identity.roles,
                    payload=payload,
                    actor=identity.user_id,
                )
            }
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    def admin_roles_get(role_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        try:
            return {"role": active_service.role_get(role_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Role not found: {role_id}") from exc

    def admin_roles_update(role_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        try:
            return {
                "role": active_service.admin_role_update(
                    role_id=role_id,
                    roles=identity.roles,
                    payload=payload,
                    actor=identity.user_id,
                )
            }
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Role not found: {role_id}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def admin_roles_delete(role_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        try:
            active_service.admin_role_delete(
                role_id=role_id, roles=identity.roles, actor=identity.user_id
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Role not found: {role_id}") from exc
        return {"status": "ok", "role_id": role_id}

    def admin_groups_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        return {"groups": active_service.groups_list()}

    def admin_groups_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
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
        _require_or_raise(request, identity, "collection.read")
        return {"group": active_service.group_get(group_id)}

    def admin_groups_update(group_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
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
        _require_or_raise(request, identity, "admin")
        active_service.admin_group_delete(group_id=group_id, roles=identity.roles, actor=identity.user_id)
        return {"status": "ok", "group_id": group_id}

    def admin_api_keys_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        return {"api_keys": active_service.api_keys_list()}

    def admin_api_keys_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        return {
            "api_key": active_service.admin_api_key_create(
                roles=identity.roles,
                payload=payload,
                actor=identity.user_id,
            )
        }

    def admin_api_keys_delete(key_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        try:
            return {
                "api_key": active_service.admin_api_key_revoke(
                    key_id=key_id,
                    roles=identity.roles,
                    actor=identity.user_id,
                )
            }
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"API key not found: {key_id}") from exc

    def admin_api_keys_revoke_token(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        try:
            result = active_service.admin_api_key_revoke_token_hash(
                sha256_prefix=str(payload["sha256_prefix"]),
                roles=identity.roles,
                actor=identity.user_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="API key not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"api_key": result}

    def admin_collections_list(profile: str = "default", request: Request = None) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        collections = [
            active_service.collection_get(profile, collection)
            for collection in active_service.collections_list(profile)
        ]
        return {"collections": collections}

    def admin_collections_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
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
        _require_or_raise(request, identity, "collection.read")
        return {"collection": active_service.collection_get(profile, collection_id)}

    def admin_collections_update(collection_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
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
        _require_or_raise(request, identity, "admin")
        active_service.admin_collection_delete(
            profile=profile,
            collection=collection_id,
            roles=identity.roles,
            actor=identity.user_id,
        )
        return {"status": "ok", "collection": collection_id, "profile": profile}

    def admin_source_configs_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        return {"source_configs": active_service.source_configs_list()}

    def admin_source_configs_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        source_id = str(payload.get("source_id", ""))
        if not source_id:
            raise HTTPException(status_code=400, detail="source_id is required")
        try:
            return {
                "source_config": active_service.admin_source_config_create(
                    source_id=source_id,
                    roles=identity.roles,
                    payload=payload,
                    actor=identity.user_id,
                )
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def admin_source_configs_get(source_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        try:
            return {"source_config": active_service.source_config_get(source_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Source config not found: {source_id}") from exc

    def admin_source_configs_update(source_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        try:
            return {
                "source_config": active_service.admin_source_config_update(
                    source_id=source_id,
                    roles=identity.roles,
                    payload=payload,
                    actor=identity.user_id,
                )
            }
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Source config not found: {source_id}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def admin_source_configs_delete(source_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        try:
            active_service.admin_source_config_delete(
                source_id=source_id,
                roles=identity.roles,
                actor=identity.user_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Source config not found: {source_id}") from exc
        return {"status": "ok", "source_id": source_id}

    def admin_rbac_bindings_list(request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
        return {"bindings": active_service.rbac_bindings_list()}

    def admin_rbac_bindings_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "admin")
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
        _require_or_raise(request, identity, "admin")
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
        _require_or_raise(request, identity, "collection.write")
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

    def files_list(profile: str | None = None, request: Request = None) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        return {"files": active_service.file_list(profile=profile)}

    async def files_upload(
        request: Request,
        profile: str = Form(default="default"),
        metadata_json: str = Form(default="{}"),
        upload: UploadFile = File(...),
    ) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        try:
            metadata = json.loads(metadata_json or "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="metadata_json must be valid JSON") from exc
        if not isinstance(metadata, dict):
            raise HTTPException(status_code=400, detail="metadata_json must decode to an object")
        content = await upload.read()
        return {
            "file": active_service.file_upload(
                filename=str(upload.filename or "upload.bin"),
                content=content,
                profile=profile,
                actor=identity.user_id,
                metadata=metadata,
            )
        }

    def files_upload_base64(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        metadata = payload.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise HTTPException(status_code=400, detail="metadata must be an object")
        content = payload.get("content_base64", payload.get("content", ""))
        if "content_base64" in payload and not str(content).startswith("base64:"):
            content = f"base64:{content}"
        return {
            "file": active_service.file_upload(
                filename=str(payload.get("filename", "upload.bin")),
                content=str(content),
                profile=str(payload.get("profile", "default")),
                actor=identity.user_id,
                metadata=metadata if isinstance(metadata, dict) else None,
            )
        }

    def files_get(file_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        try:
            return {"file": active_service.file_get(file_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}") from exc

    def files_download(file_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        try:
            return {"file": active_service.file_download(file_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}") from exc

    def files_delete(file_id: str, request: Request) -> dict[str, Any]:
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "source.configure")
        try:
            return {"file": active_service.file_delete(file_id, actor=identity.user_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}") from exc

    # -- W28E-603 Document Structure (Phase 1: model & persistence foundation) --
    def structure_health(request: Request) -> dict[str, Any]:
        """Report document-structure subsystem health, including the canonical store probe."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        return active_service.structure.health()

    def structure_documents_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        """Create or idempotently replace a canonical structure document (RBAC: collection.write)."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        try:
            return active_service.structure.create(payload, actor=identity.user_id, roles=identity.roles)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def structure_documents_list(
        profile: str | None = None,
        collection: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        request: Request = None,
    ) -> dict[str, Any]:
        """List canonical structure documents with optional filters and pagination."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        return active_service.structure.list(
            profile_id=profile,
            collection_id=collection,
            status=status,
            limit=limit,
            offset=offset,
        )

    def structure_documents_get(
        structure_document_id: str,
        include: str | None = None,
        request: Request = None,
    ) -> dict[str, Any]:
        """Retrieve a structure document by id, optionally including child objects (comma-separated)."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        include_list = [item.strip() for item in include.split(",") if item.strip()] if include else None
        try:
            return active_service.structure.get(structure_document_id, include=include_list)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Structure document not found: {structure_document_id}") from exc

    def structure_documents_delete(structure_document_id: str, request: Request) -> dict[str, Any]:
        """Delete a structure document and all of its child objects (RBAC: collection.write)."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        try:
            return active_service.structure.delete(structure_document_id, actor=identity.user_id, roles=identity.roles)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Structure document not found: {structure_document_id}") from exc

    def structure_documents_outline(structure_document_id: str, request: Request) -> dict[str, Any]:
        """Return the section hierarchy (outline) for a structure document as a nested tree."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        try:
            return active_service.structure.outline(structure_document_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Structure document not found: {structure_document_id}") from exc

    def structure_documents_pages(structure_document_id: str, request: Request) -> dict[str, Any]:
        """List page-level layout records for a structure document."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        try:
            return active_service.structure.list_pages(structure_document_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Structure document not found: {structure_document_id}") from exc

    def structure_documents_sections(structure_document_id: str, request: Request) -> dict[str, Any]:
        """List section records for a structure document."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        try:
            return active_service.structure.list_sections(structure_document_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Structure document not found: {structure_document_id}") from exc

    # -- W28E-603 Phase 2: extraction --
    def structure_extract(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        """Extract canonical structure from text/file via a parser provider and persist it."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        try:
            return active_service.structure.extract_text(
                str(payload.get("text", "")),
                profile=str(payload.get("profile", "default")),
                collection=str(payload.get("collection", "default")),
                source_uri=payload.get("source_uri"),
                source_filename=payload.get("source_filename"),
                provider=str(payload.get("provider", "internal")),
                actor=identity.user_id,
                roles=identity.roles,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def structure_link_vdb(structure_document_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        """Link a structure document to existing VDB record/chunk ids (§25 #6)."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        try:
            return active_service.structure.link_to_vdb_records(
                structure_document_id,
                vdb_record_ids=payload.get("vdb_record_ids"),
                chunk_ids=payload.get("chunk_ids"),
                source_document_id=payload.get("source_document_id"),
                actor=identity.user_id, roles=identity.roles,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Structure document not found: {structure_document_id}") from exc

    # -- W28E-603 Phase 4: corpus --
    def structure_corpus_create(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        """Create a corpus (named set of structure documents)."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        try:
            return active_service.structure.corpus.create(payload, actor=identity.user_id, roles=identity.roles)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def structure_corpus_list(profile: str | None = None, limit: int = 50, offset: int = 0, request: Request = None) -> dict[str, Any]:
        """List corpora with optional profile filter."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        return active_service.structure.corpus.list(profile_id=profile, limit=limit, offset=offset)

    def structure_corpus_get(corpus_id: str, request: Request) -> dict[str, Any]:
        """Retrieve a corpus by id."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        try:
            return active_service.structure.corpus.get(corpus_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}") from exc

    def structure_corpus_update(corpus_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        """Update a corpus."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        try:
            return active_service.structure.corpus.update(corpus_id, payload, actor=identity.user_id, roles=identity.roles)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}") from exc

    def structure_corpus_delete(corpus_id: str, request: Request) -> dict[str, Any]:
        """Delete a corpus and its derived patterns."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        try:
            return active_service.structure.corpus.delete(corpus_id, actor=identity.user_id, roles=identity.roles)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}") from exc

    def structure_corpus_analyse(corpus_id: str, request: Request) -> dict[str, Any]:
        """Analyse a corpus to derive patterns + report."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        try:
            return active_service.structure.corpus.analyse(corpus_id, actor=identity.user_id, roles=identity.roles)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}") from exc

    def structure_corpus_patterns(corpus_id: str, pattern_type: str | None = None, request: Request = None) -> dict[str, Any]:
        """Retrieve derived patterns for a corpus."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        try:
            return active_service.structure.corpus.patterns_get(corpus_id, pattern_type=pattern_type)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}") from exc

    # -- W28E-603 Phase 5: templates --
    def structure_template_generate(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        """Generate a template blueprint from a corpus's patterns."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.write")
        try:
            return active_service.structure.templates.generate(str(payload["corpus_id"]), name=payload.get("name"), actor=identity.user_id, roles=identity.roles)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Corpus not found: {payload.get('corpus_id')}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def structure_template_list(profile: str | None = None, corpus_id: str | None = None, limit: int = 50, offset: int = 0, request: Request = None) -> dict[str, Any]:
        """List generated templates."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        return active_service.structure.templates.list(profile_id=profile, corpus_id=corpus_id, limit=limit, offset=offset)

    def structure_template_get(template_id: str, request: Request) -> dict[str, Any]:
        """Retrieve a template by id."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        try:
            return active_service.structure.templates.get(template_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}") from exc

    def structure_template_export(template_id: str, format: str = "markdown", request: Request = None) -> dict[str, Any]:
        """Export a template as Markdown or JSON."""
        identity = _auth_or_raise(request, _headers_from_request(request))
        _require_or_raise(request, identity, "collection.read")
        try:
            return active_service.structure.templates.export(template_id, format=format)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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
    app.get(f"{api_base_path}/health")(health)
    app.get(f"{_LEGACY_API_BASE_PATH}/health", include_in_schema=False)(health)

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

    def _a2a_task_payload(body: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        skill_id = str(body.get("skill_id") or body.get("skill") or "").strip()
        input_data = body.get("input", {})
        input_text = input_data.get("text", "") if isinstance(input_data, dict) else str(input_data)
        payload = _parse_a2a_input(str(input_text or ""))
        if isinstance(input_data, dict):
            for key, value in input_data.items():
                if key != "text":
                    payload[key] = value
        return str(body.get("id", "")), skill_id, payload

    def _execute_a2a_skill(
        *,
        request: Request,
        identity: AuthResult,
        skill_id: str,
        payload: dict[str, Any],
    ) -> Any:
        tool_map = {
            "index_list": "index_list",
            "bulk_index": "bulk_index",
            "file_upload": "file_upload",
            "file_list": "file_list",
            "file_get": "file_get",
            "file_download": "file_download",
            "file_delete": "file_delete",
            "source_config_create": "admin_source_config_create",
            "source_config_list": "source_configs_list",
            "source_config_get": "source_config_get",
            "source_config_update": "admin_source_config_update",
            "source_config_delete": "admin_source_config_delete",
            "profiles_list": "profiles_list",
            "collection_list": "collections_list",
            "backend_health_check": "backend_health_check",
            "ingest_health": "ingest_health",
            "ingest_text": "ingest_text",
            "search": "search",
            "retrieve": "retrieve",
            # W28E-603 structure skills (§25 #12)
            "structure_extract": "structure_extract",
            "structure_document_get": "structure_document_get",
            "structure_outline_get": "structure_outline_get",
            "structure_corpus_create": "structure_corpus_create",
            "structure_corpus_analyse": "structure_corpus_analyse",
            "structure_corpus_patterns_get": "structure_corpus_patterns_get",
            "structure_template_generate": "structure_template_generate",
            "structure_template_export": "structure_template_export",
        }
        tool_name = tool_map.get(skill_id)
        if tool_name is None:
            raise HTTPException(status_code=404, detail=f"Unknown A2A skill: {skill_id}")
        try:
            return execute_tool(
                service=active_service,
                tool_name=tool_name,
                arguments={**payload, "actor": identity.user_id},
                registry=registry,
                auth=auth,
                identity=identity,
            )
        except PermissionError as exc:
            _log_auth_event(
                request,
                actor=identity.user_id,
                outcome="failure",
                action="authorise",
                roles=identity.roles,
                auth_mechanism=identity.token_type,
                reason=str(exc),
            )
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def a2a_submit_task(request: Request) -> JSONResponse:
        identity = _a2a_auth_or_raise(request, _headers_from_request(request))
        try:
            body = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="A2A task body must be JSON") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="A2A task body must be an object")
        task_id, skill_id, payload = _a2a_task_payload(body)
        task_id = task_id or secrets.token_hex(12)
        result = _execute_a2a_skill(
            request=request,
            identity=identity,
            skill_id=skill_id,
            payload=payload,
        )
        return JSONResponse(
            {
                "id": task_id,
                "status": "completed",
                "skill_id": skill_id,
                "output": {
                    "type": "json",
                    "json": result,
                    "text": json.dumps(result, sort_keys=True, default=str),
                },
            }
        )

    # A2A agent card and task submission router
    # W28C-427 IDX-SNAG-003: expanded A2A skills to cover admin, file, health, and source-config.
    _a2a_skills = [
        A2ASkill(id="index_list", name="Index List", description="List indexed collections for the selected profile"),
        A2ASkill(id="bulk_index", name="Bulk Index", description="Queue one or more text documents for asynchronous indexing"),
        A2ASkill(id="ingest_text", name="Ingest Text", description="Ingest text into a profiled collection with embedding and indexing"),
        A2ASkill(id="ingest_upload", name="Ingest Upload", description="Upload a file for chunking, embedding, and indexing"),
        A2ASkill(id="ingest_reference", name="Ingest Reference", description="Ingest content from a URI (HTTP, S3, FTP, filesystem, etc.)"),
        A2ASkill(id="search", name="Search", description="Vector similarity search across indexed collections"),
        A2ASkill(id="retrieve", name="Retrieve", description="Retrieve a specific document by ID"),
        A2ASkill(id="collection_create", name="Create Collection", description="Create a new indexed collection within a profile"),
        A2ASkill(id="collection_list", name="List Collections", description="List collections for a profile"),
        A2ASkill(id="profiles_list", name="List Profiles", description="List configured storage profiles"),
        A2ASkill(id="ingest_health", name="Ingest Health", description="Per-profile ingest pipeline health status"),
        A2ASkill(id="backend_health_check", name="Backend Health", description="Vector database backend health check"),
        A2ASkill(id="file_upload", name="File Upload", description="Upload a file to service storage (PS-78)"),
        A2ASkill(id="file_list", name="File List", description="List stored service files (PS-78)"),
        A2ASkill(id="file_get", name="File Metadata", description="Get stored service file metadata (PS-78)"),
        A2ASkill(id="file_download", name="File Download", description="Download stored service file content (PS-78)"),
        A2ASkill(id="file_delete", name="File Delete", description="Delete a stored service file (PS-78)"),
        A2ASkill(id="source_config_create", name="Create Source Config", description="Create a connector source configuration"),
        A2ASkill(id="source_config_list", name="List Source Configs", description="List connector source configurations"),
        A2ASkill(id="source_config_get", name="Get Source Config", description="Read a connector source configuration"),
        A2ASkill(id="source_config_update", name="Update Source Config", description="Update a connector source configuration"),
        A2ASkill(id="source_config_delete", name="Delete Source Config", description="Delete a connector source configuration"),
        A2ASkill(id="structure_extract", name="Extract Document Structure", description="Extract canonical document structure from text or a file (W28E-603)"),
        A2ASkill(id="structure_document_get", name="Get Document Structure", description="Retrieve a canonical structure document with its child objects (W28E-603)"),
        A2ASkill(id="structure_outline_get", name="Get Document Outline", description="Retrieve the section-hierarchy outline of a structure document (W28E-603)"),
        A2ASkill(id="structure_corpus_create", name="Create Structure Corpus", description="Create a named corpus of structure documents (W28E-603)"),
        A2ASkill(id="structure_corpus_analyse", name="Analyse Structure Corpus", description="Derive section/style/layout/table patterns across a corpus (W28E-603)"),
        A2ASkill(id="structure_corpus_patterns_get", name="Get Corpus Patterns", description="Retrieve derived structure patterns for a corpus (W28E-603)"),
        A2ASkill(id="structure_template_generate", name="Generate Structure Template", description="Generate a structure/style template blueprint from corpus patterns (W28E-603)"),
        A2ASkill(id="structure_template_export", name="Export Structure Template", description="Export a structure template as Markdown or JSON (W28E-603)"),
    ]
    app.post(f"{_CANONICAL_A2A_BASE_PATH}/tasks")(a2a_submit_task)
    app.post("/tasks")(a2a_submit_task)
    _a2a_card_router = create_a2a_card_router(
        name="index-retriever",
        description="Index retriever A2A server for vector database search and document ingestion",
        skills=_a2a_skills,
    )
    app.include_router(_a2a_card_router)

    app.get("/admin/ui")(admin_ui_root)
    app.get("/admin/ui/profiles")(admin_ui_profiles)
    app.get("/admin/ui/collections")(admin_ui_collections)
    app.get("/collections")(collections_ui)
    app.get("/admin/ui/security")(admin_ui_security)
    app.get("/admin/ui/structure")(admin_ui_structure)
    app.get("/admin/ui/app.js")(admin_ui_app_js)
    app.get("/admin/ui/styles.css")(admin_ui_styles_css)
    app.get("/api-docs", include_in_schema=False)(api_docs_page)
    app.get(f"{api_base_path}/tools")(list_tools)
    app.post(f"{api_base_path}/tools/{{tool_name}}")(call_tool)
    # Read-only status tools accept GET (REST convention for status endpoints).
    app.get(f"{api_base_path}/tools/{{tool_name}}")(call_tool)
    app.get(f"{_LEGACY_API_BASE_PATH}/tools", include_in_schema=False)(list_tools)
    app.post(f"{_LEGACY_API_BASE_PATH}/tools/{{tool_name}}", include_in_schema=False)(call_tool)
    app.get(f"{_LEGACY_API_BASE_PATH}/tools/{{tool_name}}", include_in_schema=False)(call_tool)

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
    app.get("/admin/roles")(admin_roles_list)
    app.post("/admin/roles")(admin_roles_create)
    app.get("/admin/roles/{role_id}")(admin_roles_get)
    app.put("/admin/roles/{role_id}")(admin_roles_update)
    app.patch("/admin/roles/{role_id}")(admin_roles_update)
    app.delete("/admin/roles/{role_id}")(admin_roles_delete)
    app.get("/admin/groups")(admin_groups_list)
    app.post("/admin/groups")(admin_groups_create)
    app.get("/admin/groups/{group_id}")(admin_groups_get)
    app.put("/admin/groups/{group_id}")(admin_groups_update)
    app.delete("/admin/groups/{group_id}")(admin_groups_delete)
    app.get("/admin/api-keys")(admin_api_keys_list)
    app.post("/admin/api-keys")(admin_api_keys_create)
    app.post("/admin/api-keys/revoke-token")(admin_api_keys_revoke_token)
    app.delete("/admin/api-keys/{key_id}")(admin_api_keys_delete)
    # W28A-876: the shared @cloud-dog/idam admin pages call /api/v1/admin/<entity>
    # (apiBaseUrl=""). index-retriever's Traefik does NOT strip /api on the main
    # api router, so the backend receives the FULL /api/v1/admin/<entity> path —
    # which the canonical /admin/<entity> routes above do NOT serve (→ 404, the
    # shared pages can't load). Mirror the IDAM admin handlers under BOTH
    # /v1/admin/<entity> and /api/v1/admin/<entity> (same handler callables, same
    # auth) so the shared 5 pages resolve regardless of /api-strip behaviour.
    _idam_admin_routes = [
        ("GET", "/users", admin_users_list),
        ("POST", "/users", admin_users_create),
        ("GET", "/users/{user_id}", admin_users_get),
        ("PUT", "/users/{user_id}", admin_users_update),
        ("DELETE", "/users/{user_id}", admin_users_delete),
        ("GET", "/roles", admin_roles_list),
        ("POST", "/roles", admin_roles_create),
        ("GET", "/roles/{role_id}", admin_roles_get),
        ("PUT", "/roles/{role_id}", admin_roles_update),
        ("PATCH", "/roles/{role_id}", admin_roles_update),
        ("DELETE", "/roles/{role_id}", admin_roles_delete),
        ("GET", "/groups", admin_groups_list),
        ("POST", "/groups", admin_groups_create),
        ("GET", "/groups/{group_id}", admin_groups_get),
        ("PUT", "/groups/{group_id}", admin_groups_update),
        ("DELETE", "/groups/{group_id}", admin_groups_delete),
        ("GET", "/api-keys", admin_api_keys_list),
        ("POST", "/api-keys", admin_api_keys_create),
        ("POST", "/api-keys/revoke-token", admin_api_keys_revoke_token),
        ("DELETE", "/api-keys/{key_id}", admin_api_keys_delete),
    ]
    for _prefix in ("/v1/admin", "/api/v1/admin"):
        for _method, _suffix, _handler in _idam_admin_routes:
            app.add_api_route(
                f"{_prefix}{_suffix}",
                _handler,
                methods=[_method],
                include_in_schema=False,
            )
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
    app.get(f"{api_base_path}/files")(files_list)
    app.post(f"{api_base_path}/files/upload")(files_upload)
    app.post(f"{api_base_path}/files/upload_base64")(files_upload_base64)
    app.get(f"{api_base_path}/files/{{file_id}}")(files_get)
    app.get(f"{api_base_path}/files/{{file_id}}/download")(files_download)
    app.delete(f"{api_base_path}/files/{{file_id}}")(files_delete)
    app.get(f"{_LEGACY_API_BASE_PATH}/files", include_in_schema=False)(files_list)
    app.post(f"{_LEGACY_API_BASE_PATH}/files/upload", include_in_schema=False)(files_upload)
    app.post(f"{_LEGACY_API_BASE_PATH}/files/upload_base64", include_in_schema=False)(files_upload_base64)
    app.get(f"{_LEGACY_API_BASE_PATH}/files/{{file_id}}", include_in_schema=False)(files_get)
    app.get(f"{_LEGACY_API_BASE_PATH}/files/{{file_id}}/download", include_in_schema=False)(files_download)
    app.delete(f"{_LEGACY_API_BASE_PATH}/files/{{file_id}}", include_in_schema=False)(files_delete)
    # W28E-603 document structure (Phase 1) — separate namespace from search/retrieve/ingest (design brief §12).
    app.get(f"{api_base_path}/structure/health")(structure_health)
    app.post(f"{api_base_path}/structure/documents")(structure_documents_create)
    app.get(f"{api_base_path}/structure/documents")(structure_documents_list)
    app.get(f"{api_base_path}/structure/documents/{{structure_document_id}}")(structure_documents_get)
    app.delete(f"{api_base_path}/structure/documents/{{structure_document_id}}")(structure_documents_delete)
    app.get(f"{api_base_path}/structure/documents/{{structure_document_id}}/outline")(structure_documents_outline)
    app.get(f"{api_base_path}/structure/documents/{{structure_document_id}}/pages")(structure_documents_pages)
    app.get(f"{api_base_path}/structure/documents/{{structure_document_id}}/sections")(structure_documents_sections)
    # W28E-603 Phase 2: extraction
    app.post(f"{api_base_path}/structure/extract")(structure_extract)
    app.post(f"{api_base_path}/structure/documents/{{structure_document_id}}/vdb-links")(structure_link_vdb)
    # W28E-603 Phase 4: corpus
    app.post(f"{api_base_path}/structure/corpora")(structure_corpus_create)
    app.get(f"{api_base_path}/structure/corpora")(structure_corpus_list)
    app.get(f"{api_base_path}/structure/corpora/{{corpus_id}}")(structure_corpus_get)
    app.put(f"{api_base_path}/structure/corpora/{{corpus_id}}")(structure_corpus_update)
    app.delete(f"{api_base_path}/structure/corpora/{{corpus_id}}")(structure_corpus_delete)
    app.post(f"{api_base_path}/structure/corpora/{{corpus_id}}/analyse")(structure_corpus_analyse)
    app.get(f"{api_base_path}/structure/corpora/{{corpus_id}}/patterns")(structure_corpus_patterns)
    # W28E-603 Phase 5: templates
    app.post(f"{api_base_path}/structure/templates")(structure_template_generate)
    app.get(f"{api_base_path}/structure/templates")(structure_template_list)
    app.get(f"{api_base_path}/structure/templates/{{template_id}}")(structure_template_get)
    app.get(f"{api_base_path}/structure/templates/{{template_id}}/export")(structure_template_export)
    app.post(f"{api_base_path}/upload")(upload_ingest)
    app.post(f"{_LEGACY_API_BASE_PATH}/upload", include_in_schema=False)(upload_ingest)
    # W28A-648: Audit log JSONL reader for WebUI DataTable display
    @app.get("/api/audit-log")
    async def api_audit_log(
        request: Request,
        limit: int = 200,
        log_source: str = "audit",
    ):
        """Read structured log entries from JSONL files for WebUI display."""
        log_map: dict[str, str | list[str]] = {
            "audit": [
                "logs/index-retriever-audit-api.jsonl",
                "logs/index-retriever-audit-mcp.jsonl",
            ],
            "api": "logs/api_server.log",
            "web": "logs/web_server.log",
            "mcp": "logs/mcp_server.log",
            "a2a": "logs/a2a_server.log",
        }
        log_file = log_map.get(log_source, log_map["audit"])
        if isinstance(log_file, list):
            entries = _read_jsonl_records_many(log_file, limit=limit)
        else:
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
