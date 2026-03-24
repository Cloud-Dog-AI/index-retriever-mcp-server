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

import runpy
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from index_server import api_server, mcp_server
from index_server.admin.endpoints import collection_create
from index_server.main import main
from index_server.streaming import ingest_stream_close, ingest_stream_event, ingest_stream_open
from index_tools.tools.service import IndexService
from tests.http_paths import api_tools_path, mcp_tools_path


def test_api_app_routes_cover_auth_and_errors(service: IndexService) -> None:
    # Covers: FR-01, FR-01A, FR-17
    app = api_server.build_api_app(service=service)
    client = TestClient(app)

    runtime_config = client.get("/runtime-config.js")
    assert runtime_config.status_code == 200
    assert "window.__RUNTIME_CONFIG__" in runtime_config.text
    assert "API_BASE_URL" in runtime_config.text

    root = client.get("/")
    assert root.status_code == 200
    assert "id=\"root\"" in root.text

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "id=\"root\"" in dashboard.text

    legacy_ui = client.get("/admin/ui")
    assert legacy_ui.status_code == 200
    assert "Profile management" in legacy_ui.text
    assert 'data-testid="profile-create"' in legacy_ui.text

    legacy_profiles = client.get("/admin/ui/profiles")
    assert legacy_profiles.status_code == 200
    assert "Profile management" in legacy_profiles.text
    assert 'data-testid="profile-roles"' in legacy_profiles.text

    legacy_security = client.get("/admin/ui/security")
    assert legacy_security.status_code == 200
    assert "Identity and key control" in legacy_security.text
    assert 'data-testid="user-create"' in legacy_security.text
    assert 'data-testid="group-create"' in legacy_security.text
    assert 'data-testid="api-key-create"' in legacy_security.text

    legacy_js = client.get("/admin/ui/app.js")
    assert legacy_js.status_code == 200
    assert "function createProfile" in legacy_js.text

    legacy_css = client.get("/admin/ui/styles.css")
    assert legacy_css.status_code == 200
    assert ".hero" in legacy_css.text

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    a2a_unauth = client.get("/a2a/health")
    assert a2a_unauth.status_code == 401

    a2a_auth = client.get("/a2a/health", headers={"x-api-key": "test-api-key"})
    assert a2a_auth.status_code == 200
    assert a2a_auth.json()["status"] == "ok"

    a2a_root = client.get("/a2a", headers={"x-api-key": "test-api-key"})
    assert a2a_root.status_code == 200
    assert a2a_root.json()["base_path"] == "/a2a"

    unauth = client.get(api_tools_path())
    assert unauth.status_code == 401

    tools = client.get(api_tools_path(), headers={"x-api-key": "test-api-key"})
    assert tools.status_code == 200
    assert isinstance(tools.json(), list)

    forbidden = client.post(
        api_tools_path("ingest_text"),
        headers={"authorization": "Bearer valid-reader-token"},
        json={"profile": "default", "collection": "ut_api", "text": "alpha"},
    )
    assert forbidden.status_code == 403

    bad_request = client.post(
        api_tools_path("ingest_text"),
        headers={"authorization": "Bearer valid-writer-token"},
        json={"profile": "unknown", "collection": "ut_api", "text": "alpha"},
    )
    assert bad_request.status_code == 400

    unknown = client.post(
        api_tools_path("unknown_tool"),
        headers={"x-api-key": "test-api-key"},
        json={},
    )
    assert unknown.status_code == 404


def test_api_create_runtime_app_typeerror_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyApp:
        def get(self, _path: str) -> object:
            return lambda fn: fn

        def post(self, _path: str) -> object:
            return lambda fn: fn

    def fake_create_app(**kwargs: object) -> DummyApp:
        if "title" in kwargs:
            raise TypeError("legacy signature")
        return DummyApp()

    monkeypatch.setattr(api_server, "create_app", fake_create_app)
    app = api_server._create_runtime_app()
    assert isinstance(app, DummyApp)


def test_api_run_server_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    fake_uvicorn = SimpleNamespace(
        run=lambda app, host, port, log_level: captured.update(
            {"app": app, "host": host, "port": port, "log_level": log_level}
        )
    )
    sentinel_app = object()
    monkeypatch.setattr(api_server, "build_api_app", lambda: sentinel_app)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setenv("CLOUD_DOG__INDEX__API_SERVER__HOST", "127.0.0.1")
    monkeypatch.setenv("CLOUD_DOG__INDEX__API_SERVER__PORT", "9696")

    api_server.run_api_server()
    assert captured == {"app": sentinel_app, "host": "127.0.0.1", "port": 9696, "log_level": "info"}


def test_mcp_app_and_execute_tool_paths(service: IndexService) -> None:
    app = mcp_server.build_mcp_app(service=service)
    client = TestClient(app)

    assert client.get("/health").json()["status"] == "ok"
    mcp_payload = client.get(mcp_tools_path()).json()
    assert mcp_payload["ok"] is True
    assert isinstance(mcp_payload["data"], list)

    # Optional compatibility alias: do not rely on legacy /tools for canonical contract.
    tools_payload = client.get("/tools")
    assert tools_payload.status_code in {200, 404}
    if tools_payload.status_code == 200:
        assert isinstance(tools_payload.json()["tools"], list)

    # POST canonical /mcp/tools/{tool_name} — auth required
    no_auth = client.post(mcp_tools_path("profiles_list"), json={})
    assert no_auth.status_code == 401

    # POST canonical /mcp/tools/{tool_name} — successful call
    authed = client.post(
        mcp_tools_path("profiles_list"),
        headers={"x-api-key": "test-api-key"},
        json={},
    )
    assert authed.status_code == 200
    body = authed.json()
    assert body["ok"] is True
    assert "profiles" in body["data"]

    # POST canonical /mcp/tools/{tool_name} — unknown tool
    unknown = client.post(
        mcp_tools_path("nonexistent_tool"),
        headers={"x-api-key": "test-api-key"},
        json={},
    )
    assert unknown.status_code == 404

    # POST canonical /mcp/tools/{tool_name} — permission denied
    forbidden = client.post(
        mcp_tools_path("ingest_text"),
        headers={"authorization": "Bearer valid-reader-token"},
        json={"profile": "default", "collection": "ut_mcp", "text": "blocked"},
    )
    assert forbidden.status_code == 403

    bad_payload = client.post(
        mcp_tools_path("search"),
        headers={"x-api-key": "test-api-key"},
        json={"profile": "default", "collection": "ut_mcp"},
    )
    assert bad_payload.status_code == 422

    assert mcp_server.execute_tool(service, "profiles_list", {})["profiles"] == ["default"]
    assert mcp_server.execute_tool(service, "backend_health_check", {})["status"] == "ok"
    assert mcp_server.execute_tool(service, "embedding_health_check", {})["status"] == "ok"
    assert mcp_server.execute_tool(service, "queue_status", {})["total"] >= 0
    with pytest.raises(PermissionError):
        mcp_server.execute_tool(
            service,
            "ingest_text",
            {"profile": "default", "collection": "ut_mcp", "text": "blocked"},
            identity_roles={"reader"},
        )
    with pytest.raises(KeyError):
        mcp_server.execute_tool(service, "unknown_tool", {})


def test_mcp_build_app_typeerror_fallback(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
    class DummyState:
        pass

    class DummyApp:
        state = DummyState()

        def get(self, _path: str, **kwargs: object) -> object:
            return lambda fn: fn

        def post(self, _path: str, **kwargs: object) -> object:
            return lambda fn: fn

    def fake_create_app(**kwargs: object) -> DummyApp:
        if "title" in kwargs:
            raise TypeError("legacy signature")
        return DummyApp()

    monkeypatch.setattr(mcp_server, "create_app", fake_create_app)
    app = mcp_server.build_mcp_app(service=service)
    assert isinstance(app, DummyApp)


def test_mcp_run_server_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    fake_uvicorn = SimpleNamespace(
        run=lambda app, host, port, log_level: captured.update(
            {"app": app, "host": host, "port": port, "log_level": log_level}
        )
    )
    sentinel_app = object()
    monkeypatch.setattr(mcp_server, "build_mcp_app", lambda: sentinel_app)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setenv("CLOUD_DOG__INDEX__MCP_SERVER__HOST", "127.0.0.1")
    monkeypatch.setenv("CLOUD_DOG__INDEX__MCP_SERVER__PORT", "9797")

    mcp_server.run_mcp_server()
    assert captured == {"app": sentinel_app, "host": "127.0.0.1", "port": 9797, "log_level": "info"}


def test_entrypoint_and_streaming_wrappers(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
    sentinel_app = object()
    monkeypatch.setattr("index_server.main.build_api_app", lambda: sentinel_app)
    assert main() is sentinel_app

    # Cover __main__ branch for main.py under controlled app bootstrap.
    sys.modules.pop("index_server.main", None)
    runpy.run_module("index_server.main", run_name="__main__")

    session = ingest_stream_open(service, "default", "ut_stream", "k1")
    sid = session["session_id"]
    evt = ingest_stream_event(service, sid, "stream payload", actor="writer")
    assert evt["job_id"]
    closed = ingest_stream_close(service, sid)
    assert closed["ingested_events"] == 1


def test_admin_collection_create_endpoint(service: IndexService) -> None:
    response = collection_create(service, profile="default", collection="ut_collection", roles={"admin"})
    assert response == {"status": "created", "collection": "ut_collection"}
