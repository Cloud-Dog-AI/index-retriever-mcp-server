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

"""Thin Web server for SPA delivery and API proxy helpers."""

from __future__ import annotations

import json
import os
import re

from typing import Any

from cloud_dog_api_kit import create_app
from cloud_dog_api_kit.web.proxy import WebApiProxy
from cloud_dog_config import load_config  # type: ignore
from cloud_dog_storage import path_utils
import httpx
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from index_tools.config.loader import runtime_env_files, secret_backend_kwarg
from index_server.runtime_config import resolve_server_binding

_SPA_RESERVED_SEGMENTS = {
    "api",
    "app",
    "a2a",
    "mcp",
    "auth",
    "assets",
    "health",
    "runtime-config.js",
    "docs",
    "openapi.json",
    "redoc",
    "webapi",
    "status",
    # W28E-1863 fix-wave-c (WSC-014): /version is an explicit web-tier build-identity
    # route served BEFORE the SPA catch-all — reserve it so the catch-all cannot
    # shadow it with the SPA shell / a 404.
    "version",
}

_SPA_ADMIN_PATHS = {
    "admin",
    "admin/users",
    "admin/roles",
    "admin/groups",
    "admin/api-keys",
    "admin/rbac",
    # PS-71 canonical IDAM WebUI routes (71-idam-webui.md). /admin/* retained as legacy aliases.
    "idam",
    "idam/users",
    "idam/groups",
    "idam/api-keys",
    "idam/rbac",
}

_LEGACY_WEBUI_REDIRECTS = {
    "/ui/login": "/login",
    "/audit": "/audit-log",
    "/logs": "/audit-log",
    "/idam/roles": "/admin/roles",
    "/api-keys": "/admin/api-keys",
    "/apikeys": "/admin/api-keys",
    "/rbac": "/admin/rbac",
    "/api-docs": "/developer/api-docs",
    "/docs": "/developer/api-docs",
    "/openapi": "/developer/api-docs",
    "/mcp-console": "/developer/mcp-console",
    "/a2a-console": "/developer/a2a-console",
    "/ingest-search": "/search",
    "/jobs": "/system/jobs",
    "/settings": "/system/settings",
    "/about": "/system/about",
}

# W28A-734-R2 SECURITY: paths whose authorisation MUST come from the caller's own
# session cookie or presented api-key/bearer. The web tier forwards them verbatim
# and NEVER injects the service api_key, so the api server enforces 401 for an
# unauthenticated caller. Re-narrowing this set re-opens the live /auth/me admin
# bypass — the original bc610d8 carve-out covered only /admin/<resource> and left
# /auth/me, /admin/rbac, and /api/* exposed by resolving anonymous as privileged.
_CALLER_AUTH_PREFIX_RE = re.compile(r"^/(?:auth|admin|api)(?:/|$)")


def _requires_caller_auth(proxy_path: str) -> bool:
    """True when the proxied path is identity-bearing and must be forwarded
    verbatim (no injected service api_key) so the api server enforces auth."""
    path = proxy_path if proxy_path.startswith("/") else f"/{proxy_path}"
    return bool(_CALLER_AUTH_PREFIX_RE.match(path)) or path == "/me"


def _first_role_mapped_api_key(raw: Any, role: str) -> str:
    """Return the first configured API key explicitly mapped to ``role``."""
    wanted = str(role or "").strip().lower()
    for entry in str(raw or "").split(","):
        token = entry.strip()
        if not token or ":" not in token:
            continue
        key, roles_csv = token.split(":", 1)
        roles = {item.strip().lower() for item in roles_csv.split("|") if item.strip()}
        if wanted in roles:
            return key.strip()
    return ""


def _project_root_dir() -> str:
    """Resolve the repository root for runtime assets."""
    current = path_utils.resolve_path(__file__)
    return path_utils.parent(path_utils.parent(path_utils.parent(current)))


def _ui_dist_dir() -> str:
    """Resolve the built SPA distribution directory."""
    return path_utils.join(_project_root_dir(), "ui", "dist")


def _ui_assets_dir() -> str:
    """Resolve the built SPA assets directory."""
    return path_utils.join(_ui_dist_dir(), "assets")


def _ui_index_path() -> str:
    """Resolve the built SPA index file."""
    return path_utils.join(_ui_dist_dir(), "index.html")


def _normalise_api_host(raw_host: str) -> str:
    """Convert wildcard bind addresses into a routable loopback target."""
    host = str(raw_host or "").strip()
    if host in {"0.0.0.0", "::", "[::]"}:
        return "127.0.0.1"
    return host or "127.0.0.1"


def _env_first(config: Any, *env_names: str) -> str:
    """Resolve an operator-supplied secret value via cloud_dog_config precedence.

    RULES §1.4.1: service code must not read process env directly. This helper
    resolves the dynamically-named auth/test keys through ``cloud_dog_config``
    (which already applies the ``os.environ -> env-file -> config.yaml`` chain),
    falling back to the loaded proxy config. The ``dict(os.environ)`` copy is the
    same boundary-module indirection used by ``auth.middleware._config_or_env``:
    it never reads the process environment through a direct env-getter call.
    """
    process_env = dict(os.environ)
    for env_name in env_names:
        candidates = [env_name, env_name.replace("__", ".").lower()]
        for candidate in candidates:
            try:
                value = config.get(candidate)
            except Exception:  # noqa: BLE001 - tolerate unloaded config state
                value = None
            if value is not None and str(value).strip():
                return str(value).strip()
        # Boundary fallback: operator-named secret present only in process env
        # (e.g. TEST_A2A_API_KEY) that cloud_dog_config does not model.
        raw = str(process_env.get(env_name, "")).strip()
        if raw:
            return raw
    return ""


class _ProxyConfigBridge:
    """Bridge cloud_dog_config into the keys expected by WebApiProxy."""

    def __init__(self, config: Any) -> None:
        self._config = config
        api_binding = resolve_server_binding("api_server")
        self.api_base_url = f"http://{_normalise_api_host(api_binding.host)}:{int(api_binding.port)}"

    def _configured_service_api_key(self, default: Any = None) -> Any:
        for key in (
            "api_server.api_key",
            "test.api_key",
            "auth.admin_token",
            "index.auth.admin_api_key",
        ):
            value = self._config.get(key)
            if value:
                return value

        value = _env_first(self._config, "CLOUD_DOG__INDEX__AUTH__ADMIN_API_KEY")
        if value:
            return value

        mapped_keys = self._config.get("index.auth.api_keys") or _env_first(
            self._config, "CLOUD_DOG__INDEX__AUTH__API_KEYS"
        )
        mapped_admin = _first_role_mapped_api_key(mapped_keys, "admin")
        if mapped_admin:
            return mapped_admin

        value = _env_first(self._config, "TEST_A2A_API_KEY")
        if value:
            return value

        return default

    def get(self, key: str, default: Any = None) -> Any:
        """Resolve a proxy setting through the platform configuration bridge."""
        if key in {"web_server.api_base_url", "api_server.base_url"}:
            return self.api_base_url
        if key == "web_server.verify_tls":
            return False
        if key == "api_server.api_key":
            return self._configured_service_api_key(default)
        value = self._config.get(key)
        return default if value is None else value


def _runtime_override(config: Any, env_name: str, config_key: str, default: str = "") -> str:
    """Resolve a runtime config value via cloud_dog_config, then default."""
    for key in (env_name, config_key):
        raw = str(config.get(key) or "").strip()
        if raw:
            return raw
    return default


def _runtime_override_number(config: Any, env_name: str, config_key: str, default: float) -> int | float:
    """Resolve a numeric runtime config value, preserving integers where possible."""
    raw = _runtime_override(config, env_name, config_key, str(default))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = float(default)
    return int(value) if value.is_integer() else value


def _git_head_commit() -> str:
    """Best-effort git HEAD for dev/source runs (empty string if unavailable).

    Mirrors the deployed file-mcp ``_git_head_commit`` reference (commit ``a282f7f``)
    so a local/source run still populates the WebUI About page when no container
    build-identity ENV is present.
    """
    try:
        import subprocess
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:  # noqa: BLE001 - build identity must never crash a request
        return ""
    return ""


def _build_identity(config: Any) -> dict[str, str]:
    """Return build/deploy identity for WSC-014 / PS-30 UI-R7.3.

    Source of truth is the container build: ``docker-build.sh`` stamps the image
    OCI ``org.opencontainers.image.revision`` label AND injects the matching runtime
    ENV. index-retriever's runtime-config.js already surfaces the SAME values as
    ``GIT_COMMIT`` / ``BUILD_DATE`` (config-routed via ``index.ui.git_commit`` /
    ``index.ui.build_date`` — env keys ``CLOUD_DOG__INDEX__UI__GIT_COMMIT`` /
    ``CLOUD_DOG__INDEX__UI__BUILD_DATE``, read through cloud_dog_config, NOT direct
    os.environ — RULES §1.4.1). For a dev/source run (no container ENV)
    ``source_commit`` falls back to the working-tree git HEAD so the About page is
    still populated locally. W28E-1863 fix-wave-c.
    """
    commit = _runtime_override(
        config, "CLOUD_DOG__INDEX__UI__GIT_COMMIT", "index.ui.git_commit"
    )
    if not commit or commit == "unknown":
        commit = _git_head_commit()
    build_date = _runtime_override(
        config, "CLOUD_DOG__INDEX__UI__BUILD_DATE", "index.ui.build_date"
    )
    branch = _runtime_override(
        config, "CLOUD_DOG__INDEX__UI__SOURCE_BRANCH", "index.ui.source_branch"
    )
    if branch == "unknown":
        branch = ""
    digest = _runtime_override(
        config, "CLOUD_DOG__INDEX__UI__CONTAINER_DIGEST", "index.ui.container_digest"
    )
    env_name = _runtime_override(
        config, "CLOUD_DOG_ENVIRONMENT", "service.environment"
    )
    return {
        "source_commit": commit,
        "source_branch": branch,
        "build_date": build_date,
        "container_digest": digest,
        "environment": env_name,
    }


def _redirect_with_request_parts(request: Request, target_path: str) -> RedirectResponse:
    target = target_path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    if request.url.fragment:
        target = f"{target}#{request.url.fragment}"
    return RedirectResponse(target, status_code=308)


def build_web_app() -> object:
    """Build the thin web server app."""
    # req: FR-001
    # req: FR-017
    try:
        config = load_config(
            env_files=runtime_env_files(),
            defaults_yaml="defaults.yaml",
            unresolved_policy="strict",
            **secret_backend_kwarg(False),
        )
    except Exception:
        config = load_config(
            env_files=runtime_env_files(),
            defaults_yaml="defaults.yaml",
            unresolved_policy="empty",
            **secret_backend_kwarg(False),
        )
    proxy_config = _ProxyConfigBridge(config)
    proxy = WebApiProxy.from_config(proxy_config)
    api_binding = resolve_server_binding("api_server")
    mcp_binding = resolve_server_binding("mcp_server")
    a2a_binding = resolve_server_binding("a2a_server")

    api_base_url = proxy_config.api_base_url
    mcp_base_url = f"http://{_normalise_api_host(mcp_binding.host)}:{int(mcp_binding.port)}"
    a2a_base_url = f"http://{_normalise_api_host(a2a_binding.host)}:{int(a2a_binding.port)}"

    app = create_app(
        title="index-retriever-mcp-server Web",
        version="0.1.0",
        description="Thin Web surface for index-retriever-mcp-server",
        cors_origins=["*"],
    )
    # The Web surface must expose the API server's schema/docs, not its own thin
    # proxy schema. create_app does not expose FastAPI's openapi_url toggles, so
    # remove the auto routes before the explicit proxy routes are registered.
    app.routes[:] = [
        route
        for route in app.routes
        if getattr(route, "path", None) not in {"/openapi.json", "/docs", "/redoc"}
    ]

    assets_dir = _ui_assets_dir()
    if path_utils.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="ui-assets")

    @app.middleware("http")
    async def canonical_webui_redirects(request: Request, call_next):
        if request.method in ("GET", "HEAD"):
            target = _LEGACY_WEBUI_REDIRECTS.get(request.url.path)
            if target is not None:
                return _redirect_with_request_parts(request, target)
        return await call_next(request)

    def _runtime_config_response() -> Response:
        payload = {
            "ENV": _runtime_override(config, "CLOUD_DOG_ENVIRONMENT", "service.environment", "dev"),
            "API_BASE_URL": _runtime_override(
                config,
                "CLOUD_DOG__INDEX__UI__API_BASE_URL",
                "index.ui.api_base_url",
                api_base_url,
            ),
        }
        payload["MCP_BASE_URL"] = _runtime_override(config, "CLOUD_DOG__INDEX__UI__MCP_BASE_URL", "index.ui.mcp_base_url", mcp_base_url)
        payload["A2A_BASE_URL"] = _runtime_override(config, "CLOUD_DOG__INDEX__UI__A2A_BASE_URL", "index.ui.a2a_base_url", a2a_base_url)
        payload["AUTH_MODE"] = _runtime_override(config, "CLOUD_DOG__INDEX__UI__AUTH_MODE", "index.ui.auth_mode", "cookie")
        payload["APP_VERSION"] = _runtime_override(config, "CLOUD_DOG__INDEX__UI__APP_VERSION", "index.ui.app_version", "dev")
        payload["BUILD_DATE"] = _runtime_override(config, "CLOUD_DOG__INDEX__UI__BUILD_DATE", "index.ui.build_date")
        payload["GIT_COMMIT"] = _runtime_override(config, "CLOUD_DOG__INDEX__UI__GIT_COMMIT", "index.ui.git_commit")
        payload["DEFAULT_PROFILE"] = _runtime_override(config, "CLOUD_DOG__INDEX__UI__DEFAULT_PROFILE", "index.ui.default_profile", "default")
        payload["DEFAULT_COLLECTION"] = _runtime_override(
            config,
            "CLOUD_DOG__INDEX__UI__DEFAULT_COLLECTION",
            "index.ui.default_collection",
            "w12_documents",
        )
        payload["SESSION_TIMEOUT_MINUTES"] = _runtime_override_number(
            config,
            "CLOUD_DOG__INDEX__UI__SESSION_TIMEOUT_MINUTES",
            "index.ui.session_timeout_minutes",
            30,
        )
        body = (
            "window.__RUNTIME_CONFIG__ = "
            + json.dumps(payload, ensure_ascii=True)
            + ";\n"
        )
        return Response(content=body, media_type="application/javascript")

    async def _proxy_request(path: str, request: Request) -> Response:
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in {"host", "content-length"}
        }
        body = await request.body()
        json_body: Any = None
        content_type = headers.get("content-type", "")
        if body:
            if "application/json" in content_type:
                try:
                    json_body = json.loads(body)
                except json.JSONDecodeError:
                    json_body = None

        proxy_path = path if path.startswith("/") else f"/{path}"
        # W28A-734-R2 SECURITY (generalises the W28A-876/bc610d8 admin carve-out):
        # EVERY caller-identity-bearing endpoint — /auth/* (incl. /auth/me, login,
        # logout), /me, every /admin/* (incl. rbac), and every /api/* data route —
        # must be authorised by the CALLER'S OWN session cookie or presented
        # api-key/bearer, NEVER by the service api_key that WebApiProxy injects for
        # service-to-service traffic. bc610d8 closed ONLY /admin/(users|roles|
        # groups|api-keys); the same injection still authenticated UNAUTHENTICATED
        # callers as the configured admin on /auth/me, /admin/rbac, and /api/*
        # (the live P0 bypass: anonymous GET /auth/me resolved as privileged). Forward
        # these verbatim (cookies + caller headers, NO injected key) so the api
        # server's _auth_or_raise enforces 401; the authenticated SPA forwards its
        # session cookie and still resolves to its real identity. Only non-identity
        # static paths (/app/*, /openapi.json) keep the canonical WebApiProxy hop.
        if _requires_caller_auth(proxy_path):
            async with httpx.AsyncClient(
                base_url=api_base_url,
                verify=False,
                timeout=60,
                cookies=dict(request.cookies),
            ) as client:
                raw_admin = await client.request(
                    request.method,
                    proxy_path,
                    content=body or None,
                    params=dict(request.query_params),
                    headers=headers,
                )
            return Response(
                content=raw_admin.content,
                status_code=raw_admin.status_code,
                media_type=raw_admin.headers.get("content-type", "application/json"),
                headers={
                    key: value
                    for key, value in raw_admin.headers.items()
                    if key.lower() not in {"content-length", "transfer-encoding"}
                },
            )
        if body and json_body is None and request.method.upper() in {"POST", "PUT", "PATCH"}:
            async with httpx.AsyncClient(
                base_url=api_base_url,
                verify=False,
                timeout=60,
                cookies=dict(request.cookies),
            ) as client:
                raw_response = await client.request(
                    request.method,
                    proxy_path,
                    content=body,
                    params=dict(request.query_params),
                    headers=headers,
                )
            return Response(
                content=raw_response.content,
                status_code=raw_response.status_code,
                media_type=raw_response.headers.get("content-type", "application/json"),
                headers={
                    key: value
                    for key, value in raw_response.headers.items()
                    if key.lower() not in {"content-length", "transfer-encoding"}
                },
            )

        result = await proxy.request(
            request.method,
            proxy_path,
            json=json_body,
            params=dict(request.query_params),
            headers=headers,
            cookies=dict(request.cookies),
        )
        if result.data is None:
            content: bytes | str = ""
        elif isinstance(result.data, (dict, list)):
            content = json.dumps(result.data)
        else:
            content = result.data
        return Response(
            content=content,
            status_code=result.status_code,
            media_type=result.headers.get("content-type", "application/json"),
            headers={key: value for key, value in result.headers.items() if key.lower() not in {"content-length", "transfer-encoding"}},
        )

    async def _caller_session_is_valid(request: Request) -> bool:
        """True only if the caller presents a valid cookie session."""
        return await _caller_session_payload(request) is not None

    async def _caller_session_payload(request: Request) -> dict[str, Any] | None:
        """Resolve the caller's cookie session via the api server authority.

        The probe forwards cookies only, never caller headers or an injected
        service key. A non-null payload therefore proves the cookie identity that
        must govern any web-console service-key hop.
        """
        cookies = dict(request.cookies)
        if not cookies:
            return None
        try:
            async with httpx.AsyncClient(
                base_url=api_base_url, verify=False, timeout=15, cookies=cookies
            ) as client:
                resp = await client.get("/auth/me")
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None
        try:
            payload = resp.json() or {}
        except ValueError:
            return None
        return payload if payload.get("user") else None

    def _caller_payload_has_permission(payload: dict[str, Any], permission: str) -> bool:
        user = payload.get("user")
        if not isinstance(user, dict):
            return False
        roles = {str(value).strip() for value in user.get("roles", []) if str(value).strip()}
        permissions = {str(value).strip() for value in user.get("permissions", []) if str(value).strip()}
        return "*" in permissions or permission in permissions or (permission == "admin" and "admin" in roles)

    async def _service_key_allowed(request: Request) -> bool:
        """The web tier may attach the configured service api_key to an mcp/a2a
        hop only when the caller is already authenticated — either by a real
        presented credential or a validated cookie session."""
        if request.headers.get("authorization") or request.headers.get("x-api-key"):
            return True
        return await _caller_session_is_valid(request)

    def _mcp_proxy_headers(
        request: Request,
        *,
        allow_service_key: bool = False,
        ignore_caller_credentials: bool = False,
    ) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        authorization = None if ignore_caller_credentials else request.headers.get("authorization")
        x_api_key = None if ignore_caller_credentials else request.headers.get("x-api-key")
        if authorization:
            headers["Authorization"] = authorization
        if x_api_key:
            headers["X-API-Key"] = x_api_key
        elif not authorization and allow_service_key:
            # W28A-734-R2: borrow the service api_key only for an AUTHENTICATED
            # console session; never inject it for an unauthenticated caller.
            configured_key = str(proxy_config.get("api_server.api_key", "") or "")
            if configured_key:
                headers["X-API-Key"] = configured_key
        return headers

    def _a2a_proxy_headers(request: Request, *, allow_service_key: bool = False) -> dict[str, str]:
        headers = {
            "Content-Type": request.headers.get("content-type", "application/json"),
            "Accept": request.headers.get("accept", "application/json"),
        }
        for incoming, outgoing in (
            ("authorization", "Authorization"),
            ("x-api-key", "X-API-Key"),
            ("x-correlation-id", "X-Correlation-Id"),
            ("x-request-id", "X-Request-Id"),
        ):
            value = request.headers.get(incoming)
            if value:
                headers[outgoing] = value
        if "Authorization" not in headers and "X-API-Key" not in headers and allow_service_key:
            # W28A-734-R2: only borrow the service api_key for an AUTHENTICATED caller.
            configured_key = str(proxy_config.get("api_server.api_key", "") or "")
            if configured_key:
                headers["X-API-Key"] = configured_key
        return headers

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "application": "index-retriever-mcp-server",
                "surface": "web",
                "api_base_url": api_base_url,
                "api_port": int(api_binding.port),
                "ui_dist_path": _ui_dist_dir(),
            }
        )

    @app.get("/status")
    async def status() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "surface": "web",
                "api_base_url": api_base_url,
                "mcp_base_url": mcp_base_url,
                "a2a_base_url": a2a_base_url,
            }
        )

    @app.get("/version")
    async def version_info() -> JSONResponse:
        # W28E-1863 fix-wave-c (WSC-014 / PS-30 UI-R7.3): expose source commit +
        # build date + deployment identity, not just version, so the WebUI About
        # page can render build provenance (adopts the file-mcp/search-mcp/chart-mcp
        # pattern). Registered before the SPA catch-all + reserved in
        # _SPA_RESERVED_SEGMENTS so the fallback can never shadow it. The same
        # values already flow to runtime-config.js as GIT_COMMIT/BUILD_DATE.
        _build = _build_identity(config)
        _app_version = _runtime_override(
            config, "CLOUD_DOG__INDEX__UI__APP_VERSION", "index.ui.app_version", "dev"
        )
        return JSONResponse(
            {
                "service": "index-retriever-mcp-server",
                "version": _app_version,
                "appVersion": _app_version,
                "source_commit": _build["source_commit"],
                "source_branch": _build["source_branch"],
                "build_date": _build["build_date"],
                "container_digest": _build["container_digest"],
                "environment": _build["environment"],
                # legacy field name any VersionInfo consumer may already read
                "commit": _build["source_commit"],
                "application": "index-retriever-mcp-server",
                "surface": "web",
            }
        )

    @app.get("/runtime-config.js")
    async def runtime_config() -> Response:
        return _runtime_config_response()

    @app.api_route("/webapi/proxy/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def web_api_proxy(path: str, request: Request) -> Response:
        """Proxy JSON-capable API requests through the thin web surface."""
        return await _proxy_request(path, request)

    @app.api_route("/api/v1/tools/{tool_name}", methods=["POST"])
    async def api_tool_proxy(tool_name: str, request: Request) -> Response:
        """Route WebUI tool calls through the API server authority.

        The API server owns the REST admin endpoints used by WebUI/E2E seed
        flows and exposes the same tool surface with caller-aware auth. Keeping
        Web tool calls on that surface prevents API/MCP process state splits
        while MCP-console-specific routes below still exercise MCP directly.
        """
        return await _proxy_request(f"/api/v1/tools/{tool_name}", request)

    @app.api_route("/api/v1/tools", methods=["GET"])
    async def api_tools_list(request: Request) -> Response:
        """List tools via MCP server."""
        jsonrpc_payload = {"jsonrpc": "2.0", "id": "web-tools-list", "method": "tools/list"}
        allow_service_key = await _service_key_allowed(request)
        async with httpx.AsyncClient(base_url=mcp_base_url, verify=False, timeout=30) as client:
            resp = await client.post(
                "/mcp",
                json=jsonrpc_payload,
                headers=_mcp_proxy_headers(request, allow_service_key=allow_service_key),
            )
        try:
            rpc_result = resp.json()
            tools = rpc_result.get("result", {}).get("tools", [])
            return Response(content=json.dumps(tools), media_type="application/json")
        except Exception:
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")

    @app.get("/a2a/.well-known/agent.json")
    async def a2a_agent_card() -> Response:
        """Proxy A2A agent card from the A2A server."""
        async with httpx.AsyncClient(base_url=a2a_base_url, verify=False, timeout=15) as client:
            resp = await client.get("/.well-known/agent.json")
        return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")

    @app.api_route("/a2a/{path:path}", methods=["GET", "POST"])
    async def a2a_proxy(path: str, request: Request) -> Response:
        """Proxy A2A requests to the A2A server."""
        body = await request.body()
        allow_service_key = await _service_key_allowed(request)
        async with httpx.AsyncClient(base_url=a2a_base_url, verify=False, timeout=60) as client:
            resp = await client.request(
                request.method,
                f"/{path}",
                content=body if body else None,
                params=dict(request.query_params),
                headers=_a2a_proxy_headers(request, allow_service_key=allow_service_key),
            )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json"),
            headers={
                key: value
                for key, value in resp.headers.items()
                if key.lower() not in {"content-length", "transfer-encoding"}
            },
        )

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def api_proxy(path: str, request: Request) -> Response:
        return await _proxy_request(f"/api/{path}", request)

    @app.api_route("/app/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def app_proxy(path: str, request: Request) -> Response:
        return await _proxy_request(f"/app/{path}", request)

    @app.get("/admin")
    @app.get("/admin/users")
    @app.get("/admin/roles")
    @app.get("/admin/groups")
    @app.get("/admin/api-keys")
    @app.get("/admin/rbac")
    @app.get("/idam")
    @app.get("/idam/users")
    @app.get("/idam/groups")
    @app.get("/idam/api-keys")
    @app.get("/idam/rbac")
    @app.get("/diagnostics-audit")  # W28E-614 XC-005: Audit & Log SPA route.
    async def admin_spa_routes() -> Response:
        # req: FR-018
        # PDS-009: /admin/roles MUST serve the SPA index shell for a browser HTML
        # navigation, exactly like /admin/users. Without this explicit route it fell
        # through to the /admin/{path:path} JSON proxy below (registered before the
        # SPA fallback), so the roles admin page returned application/json (roles data
        # when authed, 401 when not) instead of the SPA — blank #root in the WebUI.
        # The roles page still fetches its DATA from /api/v1/admin/roles (JSON, 401 anon).
        return _spa_index()

    @app.api_route("/admin/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def admin_proxy(path: str, request: Request) -> Response:
        return await _proxy_request(f"/admin/{path}", request)

    @app.api_route("/auth/{path:path}", methods=["GET", "POST"])
    async def auth_proxy(path: str, request: Request) -> Response:
        return await _proxy_request(f"/auth/{path}", request)

    @app.get("/openapi.json")
    async def openapi_proxy(request: Request) -> Response:
        return await _proxy_request("/openapi.json", request)

    @app.get("/docs")
    async def docs_proxy(request: Request) -> Response:
        return await _proxy_request("/docs", request)

    @app.get("/redoc")
    async def redoc_proxy(request: Request) -> Response:
        return await _proxy_request("/redoc", request)

    def _spa_index() -> Response:
        index_path = _ui_index_path()
        if not path_utils.exists(index_path):
            return HTMLResponse(content="<h1>UI not built</h1>", status_code=503)
        return FileResponse(index_path)

    @app.get("/")
    async def spa_root() -> Response:
        return _spa_index()

    @app.get("/jobs")
    async def jobs_legacy_alias(request: Request) -> Response:
        # PS-WEBUI-URL-CANONICAL WURL-002 / PS-76 JW13.1: legacy /jobs -> canonical
        # /system/jobs as a deterministic HTTP 308, preserving query string (WURL-010).
        target = "/system/jobs"
        if request.url.query:
            target = f"{target}?{request.url.query}"
        return RedirectResponse(target, status_code=308)

    @app.get("/{path:path}")
    async def spa_fallback(path: str, request: Request) -> Response:
        redirect_target = _LEGACY_WEBUI_REDIRECTS.get(f"/{path.strip('/')}")
        if redirect_target is not None:
            return _redirect_with_request_parts(request, redirect_target)
        if path in _SPA_ADMIN_PATHS:
            return _spa_index()
        first_segment = path.split("/", 1)[0]
        if first_segment in _SPA_RESERVED_SEGMENTS:
            raise HTTPException(status_code=404, detail="Not found")
        if "." in path.rsplit("/", 1)[-1]:
            candidate = path_utils.join(_ui_dist_dir(), path)
            if path_utils.exists(candidate):
                return FileResponse(candidate)
            raise HTTPException(status_code=404, detail="Not found")
        return _spa_index()

    return app


def run_web_server() -> None:
    """Run the web server on the configured host/port."""
    app = build_web_app()
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required to run Web server") from exc

    binding = resolve_server_binding("web_server")
    uvicorn.run(app, host=binding.host, port=binding.port, log_level="info")


if __name__ == "__main__":
    run_web_server()
