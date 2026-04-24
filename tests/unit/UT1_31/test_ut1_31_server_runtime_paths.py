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
import runpy
import sys
import os
from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from index_server import a2a_server, api_server, mcp_server, web_server
from index_server.admin.endpoints import collection_create
from index_server.main import main
from index_server.runtime_config import ServerBinding
from index_server.streaming import ingest_stream_close, ingest_stream_event, ingest_stream_session_start
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

    login = client.get("/login")
    assert login.status_code == 200
    assert "id=\"root\"" in login.text

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
    namespaced_health = client.get("/api/v1/health")
    assert namespaced_health.status_code == 200
    assert namespaced_health.json()["status"] == "ok"

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
    assert unauth.headers["content-type"].startswith("application/json")
    assert "Authentication failed" in unauth.text

    admin_unauth = client.get("/admin/profiles")
    assert admin_unauth.status_code == 401
    assert admin_unauth.headers["content-type"].startswith("application/json")
    assert "Authentication failed" in admin_unauth.text

    unknown_api = client.get("/api/v1/profiles")
    assert unknown_api.status_code == 404
    assert unknown_api.headers["content-type"].startswith("application/json")
    assert unknown_api.json() == {"detail": "Not found"}

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


def test_api_app_base_path_env_override_retains_legacy_compat(
    monkeypatch: pytest.MonkeyPatch, service: IndexService
) -> None:
    monkeypatch.setenv("CLOUD_DOG__INDEX_RETRIEVER__API_SERVER__BASE_PATH", "/api/v2")

    app = api_server.build_api_app(service=service)
    client = TestClient(app)

    overridden = client.get("/api/v2/health")
    assert overridden.status_code == 200
    assert overridden.json()["status"] == "ok"

    legacy = client.get("/app/v1/health")
    assert legacy.status_code == 200
    assert legacy.json()["status"] == "ok"

    stale_default = client.get("/api/v1/health")
    assert stale_default.status_code == 404


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


def test_build_log_payload_synthesises_blank_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api_server,
        "_read_jsonl_records",
        lambda _path, limit=200: [
            {
                "timestamp": "2026-04-08T15:54:07.885Z",
                "level": "INFO",
                "logger": "runtime",
                "message": "",
                "action": "create",
                "outcome": "success",
                "target": {"name": "POST /api/v1/tools/profile_get"},
            }
        ],
    )

    payload = api_server.build_log_payload(limit=10)

    assert payload["count"] == 1
    assert payload["logs"][0]["message"] == "create POST /api/v1/tools/profile_get (success)"


def test_read_jsonl_records_many_includes_rotated_siblings(tmp_path: Path) -> None:
    current = tmp_path / "audit.jsonl"
    rotated = tmp_path / "audit.jsonl.1"
    rotated_gz = tmp_path / "audit.jsonl.2.gz"

    current.write_text(json.dumps({"timestamp": "2026-04-15T07:20:36.940Z", "event_type": "security.authenticate"}) + "\n")
    rotated.write_text(json.dumps({"timestamp": "2026-04-15T07:20:35.940Z", "details": {"profile": "w28a908b_jobs_case"}}) + "\n")
    import gzip

    with gzip.open(rotated_gz, mode="wt", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": "2026-04-15T07:20:34.940Z", "details": {"job_id": "job-1"}}) + "\n")

    records = api_server._read_jsonl_records_many([str(current)], limit=10)

    assert len(records) == 3
    assert any(json.dumps(entry).find("w28a908b_jobs_case") != -1 for entry in records)
    assert any(json.dumps(entry).find("job-1") != -1 for entry in records)
    assert [entry["timestamp"] for entry in records] == [
        "2026-04-15T07:20:34.940Z",
        "2026-04-15T07:20:35.940Z",
        "2026-04-15T07:20:36.940Z",
    ]


def test_api_run_server_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    api_port = int(os.environ.get("CLOUD_DOG__API_SERVER__PORT", "8074"))
    captured: dict[str, object] = {}
    fake_uvicorn = SimpleNamespace(
        run=lambda app, host, port, log_level: captured.update(
            {"app": app, "host": host, "port": port, "log_level": log_level}
        )
    )
    sentinel_app = object()
    monkeypatch.setattr(api_server, "build_api_app", lambda: sentinel_app)
    monkeypatch.setattr(
        api_server,
        "resolve_server_binding",
        lambda _name: ServerBinding(host="127.0.0.1", port=api_port),
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    api_server.run_api_server()
    assert captured == {
        "app": sentinel_app,
        "host": "127.0.0.1",
        "port": api_port,
        "log_level": "info",
    }


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
    assert forbidden.json()["detail"] == "Authorisation failed for tool 'ingest_text'"

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

        # Added for cloud_dog_api_kit>=0.9.0 mcp.transport.register_mcp_routes
        # which also registers a DELETE handler. W28A-1002-EXTEND-R2 Phase B.
        def delete(self, _path: str, **kwargs: object) -> object:
            return lambda fn: fn

    def fake_create_app(**kwargs: object) -> DummyApp:
        if "title" in kwargs:
            raise TypeError("legacy signature")
        return DummyApp()

    monkeypatch.setattr(mcp_server, "create_app", fake_create_app)
    app = mcp_server.build_mcp_app(service=service)
    assert isinstance(app, DummyApp)


def test_mcp_run_server_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    mcp_port = int(os.environ.get("CLOUD_DOG__MCP_SERVER__PORT", "8076"))
    captured: dict[str, object] = {}
    fake_uvicorn = SimpleNamespace(
        run=lambda app, host, port, log_level: captured.update(
            {"app": app, "host": host, "port": port, "log_level": log_level}
        )
    )
    sentinel_app = object()
    monkeypatch.setattr(mcp_server, "build_mcp_app", lambda: sentinel_app)
    monkeypatch.setattr(
        mcp_server,
        "resolve_server_binding",
        lambda _name: ServerBinding(host="127.0.0.1", port=mcp_port),
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    mcp_server.run_mcp_server()
    assert captured == {
        "app": sentinel_app,
        "host": "127.0.0.1",
        "port": mcp_port,
        "log_level": "info",
    }


def test_entrypoint_and_streaming_wrappers(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
    sentinel_app = object()
    monkeypatch.setattr("index_server.main.build_api_app", lambda: sentinel_app)
    assert main() is sentinel_app

    # Cover __main__ branch for main.py under controlled app bootstrap.
    sys.modules.pop("index_server.main", None)
    runpy.run_module("index_server.main", run_name="__main__")

    session = ingest_stream_session_start(service, "default", "ut_stream", "k1")
    sid = session["session_id"]
    evt = ingest_stream_event(service, sid, "stream payload", actor="writer")
    assert evt["job_id"]
    closed = ingest_stream_close(service, sid)
    assert closed["ingested_events"] == 1


def test_admin_collection_create_endpoint(service: IndexService) -> None:
    response = collection_create(service, profile="default", collection="ut_collection", roles={"admin"})
    assert response == {"status": "created", "collection": "ut_collection"}


def test_build_status_payload_counts_active_documents_from_runtime(service: IndexService) -> None:
    service.ingest_text("default", "status_cov", "status payload active doc", "api://status-cov", actor="writer")
    deleted_job_id = service.ingest_text("default", "status_cov", "status payload deleted doc", "api://status-deleted", actor="writer")
    assert deleted_job_id
    deleted_record = next(record for record in service.documents.values() if record.source == "api://status-deleted")
    assert service.delete_by_id("default", "status_cov", str(deleted_record.record_id or deleted_record.doc_id)) is True

    payload = api_server.build_status_payload(service)

    assert payload["document_count"] >= 1
    assert payload["collection_count"] >= 1


def test_web_run_server_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    web_port = int(os.environ.get("CLOUD_DOG__WEB_SERVER__PORT", "8075"))
    captured: dict[str, object] = {}
    fake_uvicorn = SimpleNamespace(
        run=lambda app, host, port, log_level: captured.update(
            {"app": app, "host": host, "port": port, "log_level": log_level}
        )
    )
    sentinel_app = object()
    monkeypatch.setattr(web_server, "build_web_app", lambda: sentinel_app)
    monkeypatch.setattr(
        web_server,
        "resolve_server_binding",
        lambda _name: ServerBinding(host="127.0.0.1", port=web_port),
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    web_server.run_web_server()
    assert captured == {
        "app": sentinel_app,
        "host": "127.0.0.1",
        "port": web_port,
        "log_level": "info",
    }


def test_web_runtime_config_and_spa_admin_routes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyConfig:
        def get(self, key: str, default: object = None) -> object:
            values = {
                "service.environment": "staging",
                "index.ui.auth_mode": "api_key",
                "index.ui.app_version": "test",
                "index.ui.default_profile": "default",
                "index.ui.default_collection": "w12_documents",
                "index.ui.session_timeout_minutes": "5.5",
                "test.api_key": "test-api-key",
            }
            return values.get(key, default)

    class DummyProxy:
        async def request(self, method: str, path: str, **_kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                status_code=401 if path == "/admin/profiles" else 200,
                data={"detail": "Authentication failed"} if path == "/admin/profiles" else {"status": "ok"},
                headers={"content-type": "application/json"},
            )

    index_path = tmp_path / "index.html"
    index_path.write_text("<html><body><div id='root'></div></body></html>", encoding="utf-8")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    monkeypatch.setattr(web_server, "load_config", lambda **_kwargs: DummyConfig())
    monkeypatch.setattr(web_server, "runtime_env_files", lambda: [])
    monkeypatch.setattr(web_server, "_ui_index_path", lambda: index_path)
    monkeypatch.setattr(web_server, "_ui_dist_dir", lambda: tmp_path)
    monkeypatch.setattr(web_server, "_ui_assets_dir", lambda: assets_dir)
    monkeypatch.setattr(
        web_server,
        "resolve_server_binding",
        lambda name: {
            "api_server": ServerBinding(host="127.0.0.1", port=8074),
            "mcp_server": ServerBinding(host="127.0.0.1", port=8076),
            "a2a_server": ServerBinding(host="127.0.0.1", port=8077),
        }[name],
    )
    monkeypatch.setattr(web_server.WebApiProxy, "from_config", classmethod(lambda cls, _config: DummyProxy()))

    client = TestClient(web_server.build_web_app())

    runtime_config = client.get("/runtime-config.js")
    assert runtime_config.status_code == 200
    assert '"SESSION_TIMEOUT_MINUTES": 5.5' in runtime_config.text

    spa_admin = client.get("/admin/users")
    assert spa_admin.status_code == 200
    assert "id='root'" in spa_admin.text

    proxied_admin = client.get("/admin/profiles")
    assert proxied_admin.status_code == 401
    assert proxied_admin.json() == {"detail": "Authentication failed"}


def test_a2a_run_server_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    a2a_port = int(os.environ.get("CLOUD_DOG__A2A_SERVER__PORT", "8077"))
    captured: dict[str, object] = {}
    fake_uvicorn = SimpleNamespace(
        run=lambda app, host, port, log_level: captured.update(
            {"app": app, "host": host, "port": port, "log_level": log_level}
        )
    )
    sentinel_app = object()
    monkeypatch.setattr(a2a_server, "build_a2a_app", lambda: sentinel_app)
    monkeypatch.setattr(
        a2a_server,
        "resolve_server_binding",
        lambda _name: ServerBinding(host="127.0.0.1", port=a2a_port),
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    a2a_server.run_a2a_server()
    assert captured == {
        "app": sentinel_app,
        "host": "127.0.0.1",
        "port": a2a_port,
        "log_level": "info",
    }
