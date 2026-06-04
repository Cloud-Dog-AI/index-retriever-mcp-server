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

from typing import Any

from cloud_dog_api_kit import create_app
from cloud_dog_api_kit.web.proxy import WebApiProxy
from cloud_dog_config import load_config  # type: ignore
from cloud_dog_storage import path_utils
import httpx
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from index_server.admin_ui import collections_page
from index_tools.config.loader import runtime_env_files
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
}

_SPA_ADMIN_PATHS = {
    "admin",
    "admin/users",
    "admin/groups",
    "admin/api-keys",
    "admin/rbac",
}


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


class _ProxyConfigBridge:
    """Bridge cloud_dog_config into the keys expected by WebApiProxy."""

    def __init__(self, config: Any) -> None:
        self._config = config
        api_binding = resolve_server_binding("api_server")
        self.api_base_url = f"http://{_normalise_api_host(api_binding.host)}:{int(api_binding.port)}"

    def get(self, key: str, default: Any = None) -> Any:
        if key in {"web_server.api_base_url", "api_server.base_url"}:
            return self.api_base_url
        if key == "web_server.verify_tls":
            return False
        if key == "api_server.api_key":
            return self._config.get("api_server.api_key") or self._config.get("test.api_key") or self._config.get("auth.admin_token") or default
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


def build_web_app() -> object:
    """Build the thin web server app."""
    try:
        config = load_config(
            env_files=runtime_env_files(),
            defaults_yaml="defaults.yaml",
            unresolved_policy="strict",
            vault_enabled=True,
        )
    except Exception:
        config = load_config(
            env_files=runtime_env_files(),
            defaults_yaml="defaults.yaml",
            unresolved_policy="empty",
            vault_enabled=False,
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

    assets_dir = _ui_assets_dir()
    if path_utils.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="ui-assets")

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

    def _mcp_proxy_headers(request: Request) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        authorization = request.headers.get("authorization")
        x_api_key = request.headers.get("x-api-key")
        if authorization:
            headers["Authorization"] = authorization
        if x_api_key:
            headers["X-API-Key"] = x_api_key
        elif not authorization:
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
    async def version() -> JSONResponse:
        # W28E-614 XC-001: live version banner reads {"version": "..."} from this endpoint.
        # The runtime-config APP_VERSION reflects the deployed image's baked version.
        app_version = _runtime_override(config, "CLOUD_DOG__INDEX__UI__APP_VERSION", "index.ui.app_version", "dev")
        return JSONResponse(
            {
                "version": str(app_version),
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
        """Route tool calls to the MCP server which owns the live IndexService state."""
        body = await request.body()
        tool_args: dict = {}
        if body:
            try:
                tool_args = json.loads(body)
            except json.JSONDecodeError:
                pass
        jsonrpc_payload = {
            "jsonrpc": "2.0",
            "id": "web-tool-proxy",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": tool_args},
        }
        async with httpx.AsyncClient(base_url=mcp_base_url, verify=False, timeout=60) as client:
            resp = await client.post(
                "/mcp",
                json=jsonrpc_payload,
                headers=_mcp_proxy_headers(request),
            )
        try:
            rpc_result = resp.json()
            structured = rpc_result.get("result", {}).get("structuredContent")
            if structured is not None:
                return Response(content=json.dumps(structured), media_type="application/json")
            content_items = rpc_result.get("result", {}).get("content", [])
            if content_items and isinstance(content_items[0], dict) and content_items[0].get("text"):
                return Response(content=content_items[0]["text"], media_type="application/json")
        except Exception:
            pass
        return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")

    @app.api_route("/api/v1/tools", methods=["GET"])
    async def api_tools_list(request: Request) -> Response:
        """List tools via MCP server."""
        jsonrpc_payload = {"jsonrpc": "2.0", "id": "web-tools-list", "method": "tools/list"}
        async with httpx.AsyncClient(base_url=mcp_base_url, verify=False, timeout=30) as client:
            resp = await client.post(
                "/mcp",
                json=jsonrpc_payload,
                headers=_mcp_proxy_headers(request),
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
        async with httpx.AsyncClient(base_url=a2a_base_url, verify=False, timeout=60) as client:
            resp = await client.request(request.method, f"/{path}", content=body if body else None,
                                        headers={"Content-Type": request.headers.get("content-type", "application/json")})
        return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def api_proxy(path: str, request: Request) -> Response:
        return await _proxy_request(f"/api/{path}", request)

    @app.api_route("/app/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def app_proxy(path: str, request: Request) -> Response:
        return await _proxy_request(f"/app/{path}", request)

    @app.get("/admin")
    @app.get("/admin/users")
    @app.get("/admin/groups")
    @app.get("/admin/api-keys")
    @app.get("/admin/rbac")
    @app.get("/admin/roles")  # W28E-614 CX-110: new role policies page route.
    @app.get("/diagnostics-audit")  # W28E-614 XC-005: Audit & Log SPA route.
    async def admin_spa_routes() -> Response:
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

    @app.get("/collections")
    async def collections_ui() -> HTMLResponse:
        return HTMLResponse(content=collections_page())

    @app.get("/{path:path}")
    async def spa_fallback(path: str) -> Response:
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
