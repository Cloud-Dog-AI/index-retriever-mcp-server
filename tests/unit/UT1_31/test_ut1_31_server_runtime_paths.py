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

import base64
import json
import runpy
import sys
import os
from hashlib import sha256
from types import SimpleNamespace
from pathlib import Path
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from index_server import a2a_server, api_server, mcp_server, web_server
from index_server.admin.endpoints import collection_create
from index_server.main import main
from index_server.runtime_config import ServerBinding
from index_server.streaming import ingest_stream_close, ingest_stream_event, ingest_stream_session_start
from index_tools.tools.service import DocumentRecord, IndexService
from tests.http_paths import api_tools_path, mcp_tools_path
@pytest.mark.UT
@pytest.mark.req("CS-011")  # W28C-1711-R3.5 binding
@pytest.mark.req("CS-008")  # W28C-1711-R3.5 binding
@pytest.mark.req("CS-005")  # W28C-1711-R3.5 binding
@pytest.mark.req("CS-003")  # W28C-1711-R3.5 binding
@pytest.mark.req("CS-002")  # W28C-1711-R3.5 binding
@pytest.mark.req("CS-001")  # W28C-1711-R3.5 binding
@pytest.mark.mcp
@pytest.mark.req("FR-001")


def test_api_app_routes_cover_auth_and_errors(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
    # Covers: FR-01, FR-01A, FR-17
    web_credential = "pw-" + sha256(b"w28a734-flat-login").hexdigest()[:12]
    original_load_runtime_config = api_server.load_runtime_config

    def _load_test_runtime_config(*args: object, **kwargs: object) -> object:
        runtime_cfg = original_load_runtime_config(*args, **kwargs)
        runtime_cfg.web_login.username = "admin"
        runtime_cfg.web_login.password = web_credential
        runtime_cfg.web_login.read_write_username = "read-write"
        runtime_cfg.web_login.read_write_password = web_credential
        runtime_cfg.web_login.read_only_username = "read-only"
        runtime_cfg.web_login.read_only_password = web_credential
        return runtime_cfg

    monkeypatch.setattr(api_server, "load_runtime_config", _load_test_runtime_config)
    collection_create(service, profile="default", collection="ut_visible_collection", roles={"admin"})
    app = api_server.build_api_app(service=service)
    client = TestClient(app)

    runtime_config = client.get("/runtime-config.js")
    assert runtime_config.status_code == 200
    assert "window.__RUNTIME_CONFIG__" in runtime_config.text
    assert "API_BASE_URL" in runtime_config.text
    assert '"AUTH_MODE": "cookie"' in runtime_config.text

    legacy_mcp = client.get("/mcp-console?tool=index_list", follow_redirects=False)
    assert legacy_mcp.status_code == 308
    assert legacy_mcp.headers["location"] == "/developer/mcp-console?tool=index_list"

    canonical_mcp = client.get("/developer/mcp-console")
    assert canonical_mcp.status_code == 200

    # W28E-1844 / PS-WEBUI-URL-CANONICAL WURL-DEV-A2A: the public api_server SPA front
    # must 308 legacy /a2a-console -> canonical /developer/a2a-console (query preserved).
    legacy_a2a = client.get("/a2a-console?skill=ping", follow_redirects=False)
    assert legacy_a2a.status_code == 308
    assert legacy_a2a.headers["location"] == "/developer/a2a-console?skill=ping"

    canonical_a2a = client.get("/developer/a2a-console")
    assert canonical_a2a.status_code == 200

    anon_me = client.get("/auth/me")
    assert anon_me.status_code == 401
    assert "admin" not in anon_me.text

    read_only_me = client.get("/auth/me", headers={"x-api-key": "valid-reader-token"})
    assert read_only_me.status_code == 200
    assert read_only_me.json()["user"]["roles"] == ["read-only"]
    assert "admin" not in read_only_me.json()["user"]["roles"]

    read_write_me = client.get("/auth/me", headers={"x-api-key": "valid-writer-token"})
    assert read_write_me.status_code == 200
    assert read_write_me.json()["user"]["roles"] == ["read-write"]

    admin_me = client.get("/auth/me", headers={"x-api-key": "valid-admin-token"})
    assert admin_me.status_code == 200
    assert admin_me.json()["user"]["roles"] == ["admin"]

    for username, expected_roles, expected_permissions in (
        ("admin", ["admin"], {"*"}),
        ("read-write", ["read-write"], {"collection.read", "collection.write"}),
        ("read-only", ["read-only"], {"collection.read"}),
    ):
        client.post("/auth/logout")
        login = client.post("/auth/login", json={"username": username, "password": web_credential})
        assert login.status_code == 200, login.text
        assert login.json()["user"]["roles"] == expected_roles
        assert expected_permissions.issubset(set(login.json()["user"]["permissions"]))
        me = client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["roles"] == expected_roles
        assert expected_permissions.issubset(set(me.json()["user"]["permissions"]))

    read_only_write = client.post(
        "/api/v1/tools/ingest_text",
        json={
            "profile": "default",
            "collection": "ut_visible_collection",
            "text": "read-only write must fail",
            "source": "file://unit/read-only.txt",
        },
    )
    assert read_only_write.status_code == 403
    assert "admin" not in read_only_write.text

    read_only_mixed_auth_write = client.post(
        "/api/v1/tools/ingest_text",
        headers={"x-api-key": "valid-admin-token"},
        json={
            "profile": "default",
            "collection": "ut_visible_collection",
            "text": "read-only cookie must override injected API key",
            "source": "file://unit/read-only-mixed-auth.txt",
        },
    )
    assert read_only_mixed_auth_write.status_code == 403
    assert "admin" not in read_only_mixed_auth_write.text

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

    legacy_collections = client.get("/admin/ui/collections")
    assert legacy_collections.status_code == 200
    assert "Collection inventory" in legacy_collections.text
    assert 'data-testid="collections-table-body"' in legacy_collections.text
    assert "ut_visible_collection" in legacy_collections.text

    # IR-COLL-SHADOW (W28E-1863): a hard GET of /collections must serve the SPA
    # shell, NOT the legacy server-rendered "Collection inventory" page that
    # previously shadowed the SPA CollectionCrudPage. The legacy inventory stays
    # reachable only at /admin/ui/collections (asserted above).
    collections_route = client.get("/collections")
    assert collections_route.status_code == 200
    assert 'id="root"' in collections_route.text
    assert "Collection inventory" not in collections_route.text
    assert 'data-testid="collections-table-body"' not in collections_route.text

    legacy_security = client.get("/admin/ui/security")
    assert legacy_security.status_code == 200
    assert "Identity and key control" in legacy_security.text
    assert 'data-testid="user-create"' in legacy_security.text
    assert 'data-testid="group-create"' in legacy_security.text
    assert 'data-testid="api-key-create"' in legacy_security.text

    legacy_js = client.get("/admin/ui/app.js")
    assert legacy_js.status_code == 200
    assert "function createProfile" in legacy_js.text
    assert "function refreshCollections" in legacy_js.text

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

    client.post("/auth/logout")
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

    created_key = client.post(
        "/admin/api-keys",
        headers={"authorization": "Bearer valid-admin-token"},
        json={"key_id": "unit-hash-revoke", "label": "Unit Hash Revoke", "roles": ["viewer"]},
    )
    assert created_key.status_code == 200, created_key.text
    raw_key = created_key.json()["api_key"]["token"]
    revoke_hash = client.post(
        "/admin/api-keys/revoke-token",
        headers={"authorization": "Bearer valid-admin-token"},
        json={"sha256_prefix": sha256(raw_key.encode("utf-8")).hexdigest()[:12]},
    )
    assert revoke_hash.status_code == 200, revoke_hash.text
    assert revoke_hash.json()["api_key"]["revoked_count"] == 1
    revoked_denied = client.get("/api/v1/tools", headers={"x-api-key": raw_key})
    assert revoked_denied.status_code == 401

    bad_source_type = client.post(
        "/admin/source-configs",
        headers={"authorization": "Bearer valid-admin-token"},
        json={
            "source_id": "ut-bad-source-type",
            "source_type": "ssh",
            "uri": "ssh://example.com/source.txt",
            "profile": "default",
            "collection": "ut_api",
        },
    )
    assert bad_source_type.status_code == 400
    assert "Unsupported source type" in bad_source_type.text

    bad_gdrive = client.post(
        "/admin/source-configs",
        headers={"authorization": "Bearer valid-admin-token"},
        json={
            "source_id": "ut-bad-gdrive",
            "source_type": "gdrive",
            "uri": "https://example.com/not-drive",
            "profile": "default",
            "collection": "ut_api",
        },
    )
    assert bad_gdrive.status_code == 400
    assert "Google Drive file ID is required" in bad_gdrive.text

    file_upload = client.post(
        "/api/v1/files/upload_base64",
        headers={"authorization": "Bearer valid-admin-token"},
        json={
            "filename": "ut-file-lifecycle.txt",
            "content_base64": base64.b64encode(b"unit file lifecycle").decode("ascii"),
            "profile": "default",
        },
    )
    assert file_upload.status_code == 200, file_upload.text
    file_id = file_upload.json()["file"]["file_id"]

    file_list = client.get("/api/v1/files?profile=default", headers={"authorization": "Bearer valid-admin-token"})
    assert file_list.status_code == 200
    assert any(item["file_id"] == file_id for item in file_list.json()["files"])

    file_get = client.get(f"/api/v1/files/{file_id}", headers={"authorization": "Bearer valid-admin-token"})
    assert file_get.status_code == 200
    assert file_get.json()["file"]["filename"] == "ut-file-lifecycle.txt"

    file_download = client.get(f"/api/v1/files/{file_id}/download", headers={"authorization": "Bearer valid-admin-token"})
    assert file_download.status_code == 200
    assert base64.b64decode(file_download.json()["file"]["content_base64"]) == b"unit file lifecycle"

    file_delete = client.delete(f"/api/v1/files/{file_id}", headers={"authorization": "Bearer valid-admin-token"})
    assert file_delete.status_code == 200
    assert file_delete.json()["file"]["status"] == "deleted"

    file_missing = client.get(f"/api/v1/files/{file_id}", headers={"authorization": "Bearer valid-admin-token"})
    assert file_missing.status_code == 404

    card = client.get("/.well-known/agent.json")
    assert card.status_code == 200
    card_skills = {item["id"] for item in card.json()["skills"]}
    assert {"file_upload", "file_list", "file_get", "file_download", "file_delete"}.issubset(card_skills)

    a2a_missing_auth = client.post(
        "/a2a/tasks",
        json={"id": "ut-a2a-denied", "skill_id": "file_list", "input": {"text": "{}"}},
    )
    assert a2a_missing_auth.status_code == 401

    a2a_upload = client.post(
        "/a2a/tasks",
        headers={"authorization": "Bearer valid-admin-token"},
        json={
            "id": "ut-a2a-upload",
            "skill_id": "file_upload",
            "input": {"text": json.dumps({"filename": "ut-a2a.txt", "content": "a2a lifecycle", "profile": "default"})},
        },
    )
    assert a2a_upload.status_code == 200, a2a_upload.text
    a2a_file_id = a2a_upload.json()["output"]["json"]["file_id"]

    a2a_download = client.post(
        "/a2a/tasks",
        headers={"authorization": "Bearer valid-admin-token"},
        json={"id": "ut-a2a-download", "skill_id": "file_download", "input": {"text": json.dumps({"file_id": a2a_file_id})}},
    )
    assert a2a_download.status_code == 200, a2a_download.text
    encoded = a2a_download.json()["output"]["json"]["content_base64"]
    assert base64.b64decode(encoded) == b"a2a lifecycle"

    a2a_delete = client.post(
        "/a2a/tasks",
        headers={"authorization": "Bearer valid-admin-token"},
        json={"id": "ut-a2a-delete", "skill_id": "file_delete", "input": {"text": json.dumps({"file_id": a2a_file_id})}},
    )
    assert a2a_delete.status_code == 200, a2a_delete.text

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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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

    with pytest.raises(PermissionError):
        mcp_server.execute_tool(service, "profiles_list", {})

    profiles = mcp_server.execute_tool(service, "profiles_list", {}, identity_roles={"reader"})["profiles"]
    assert "default" in profiles
    assert (
        mcp_server.execute_tool(service, "backend_health_check", {}, identity_roles={"reader"})["status"] == "ok"
    )
    assert (
        mcp_server.execute_tool(service, "embedding_health_check", {}, identity_roles={"reader"})["status"] == "ok"
    )
    assert mcp_server.execute_tool(service, "queue_status", {}, identity_roles={"writer"})["total"] >= 0
    with pytest.raises(PermissionError):
        mcp_server.execute_tool(
            service,
            "ingest_text",
            {"profile": "default", "collection": "ut_mcp", "text": "blocked"},
            identity_roles={"reader"},
        )
    with pytest.raises(KeyError):
        mcp_server.execute_tool(service, "unknown_tool", {})
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


def test_admin_collection_create_endpoint(service: IndexService) -> None:
    response = collection_create(service, profile="default", collection="ut_collection", roles={"admin"})
    assert response == {"status": "created", "collection": "ut_collection"}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


def test_build_status_payload_counts_active_documents_from_runtime(service: IndexService) -> None:
    collection_create(service, profile="default", collection="status_cov", roles={"admin"})
    created_at = datetime.now(timezone.utc)
    service.documents["active-status-cov"] = DocumentRecord(
        doc_id="active-status-cov",
        record_id="active-status-cov",
        profile="default",
        collection="status_cov",
        source="api://status-cov",
        text="status payload active doc",
        metadata={
            "doc_id": "active-status-cov",
            "record_id": "active-status-cov",
            "lifecycle_state": "active",
            "is_latest": True,
        },
        created_at=created_at,
    )
    service.documents["deleted-status-cov"] = DocumentRecord(
        doc_id="deleted-status-cov",
        record_id="deleted-status-cov",
        profile="default",
        collection="status_cov",
        source="api://status-deleted",
        text="status payload deleted doc",
        metadata={
            "doc_id": "deleted-status-cov",
            "record_id": "deleted-status-cov",
            "lifecycle_state": "deleted",
            "is_latest": True,
        },
        created_at=created_at,
    )

    payload = api_server.build_status_payload(service)

    assert payload["document_count"] == 1
    assert payload["collection_count"] >= 1
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


def test_web_runtime_config_and_spa_admin_routes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyConfig:
        def get(self, key: str, default: object = None) -> object:
            values = {
                "service.environment": "staging",
                "index.ui.auth_mode": "cookie",
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

    # W28A-734-R2: identity-bearing proxy paths (/auth/*, /admin/*, /api/*) are now
    # forwarded VERBATIM through a raw httpx hop (no injected service api_key), so
    # the api server enforces auth. Emulate that upstream with a MockTransport that
    # denies (401) any request without a real caller credential and records every
    # forwarded request, so the test can prove the web tier injects NOTHING.
    captured_requests: list[httpx.Request] = []

    def _upstream_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        has_cred = bool(request.headers.get("x-api-key") or request.headers.get("authorization"))
        if not has_cred:
            return httpx.Response(401, json={"detail": "Authentication failed"})
        if request.url.path == "/auth/me":
            return httpx.Response(
                200,
                json={"user": {"id": "configured:deadbeef0001", "roles": ["admin"], "permissions": ["*"]}},
            )
        return httpx.Response(200, json={"status": "ok"})

    _mock_transport = httpx.MockTransport(_upstream_handler)
    _real_async_client = web_server.httpx.AsyncClient

    def _mock_async_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = _mock_transport
        return _real_async_client(*args, **kwargs)

    monkeypatch.setattr(web_server.httpx, "AsyncClient", _mock_async_client)

    client = TestClient(web_server.build_web_app())

    runtime_config = client.get("/runtime-config.js")
    assert runtime_config.status_code == 200
    assert '"SESSION_TIMEOUT_MINUTES": 5.5' in runtime_config.text

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert openapi.json() == {"status": "ok"}
    assert not any(r.url.path == "/openapi.json" for r in captured_requests)

    spa_admin = client.get("/admin/users")
    assert spa_admin.status_code == 200
    assert "id='root'" in spa_admin.text

    # PDS-009: a browser HTML navigation to /admin/roles (where /idam/roles 308s to)
    # MUST serve the SPA index shell — 200 text/html with #root — exactly like
    # /admin/users, NOT the /admin/{path} JSON proxy that previously shadowed it.
    spa_roles = client.get("/admin/roles")
    assert spa_roles.status_code == 200
    assert spa_roles.headers["content-type"].startswith("text/html")
    assert "id='root'" in spa_roles.text

    legacy_mcp = client.get("/mcp-console?tool=index_list", follow_redirects=False)
    assert legacy_mcp.status_code == 308
    assert legacy_mcp.headers["location"] == "/developer/mcp-console?tool=index_list"

    canonical_mcp = client.get("/developer/mcp-console")
    assert canonical_mcp.status_code == 200
    assert "id='root'" in canonical_mcp.text

    # IR-COLL-SHADOW (W28E-1863): a browser HTML navigation to /collections MUST
    # serve the SPA index shell (200 text/html with #root), exactly like the other
    # SPA routes. Previously the web tier registered a concrete /collections route
    # that served the legacy server-rendered "Collection inventory" page, shadowing
    # the SPA CollectionCrudPage and creating an /admin/ui/* navigation dead-end.
    collections_ui = client.get("/collections")
    assert collections_ui.status_code == 200
    assert collections_ui.headers["content-type"].startswith("text/html")
    assert "id='root'" in collections_ui.text
    assert "Collection inventory" not in collections_ui.text
    assert 'data-testid="collections-table-body"' not in collections_ui.text

    # Proxied admin endpoint, UNAUTHENTICATED, is forwarded verbatim and denied 401.
    proxied_admin = client.get("/admin/profiles")
    assert proxied_admin.status_code == 401
    assert proxied_admin.json() == {"detail": "Authentication failed"}

    # W28A-734-R2 NEGATIVE-AUTH (the live P0 bypass regression guard):
    # an UNAUTHENTICATED /auth/me must be denied — NEVER an admin/configured
    # principal — and the web tier must NOT inject the service api_key on the hop.
    me_unauth = client.get("/auth/me")
    assert me_unauth.status_code == 401, me_unauth.text
    assert "configured:" not in me_unauth.text and "permissions" not in me_unauth.text
    me_unauth_hops = [r for r in captured_requests if r.url.path == "/auth/me"]
    assert me_unauth_hops, "web tier did not forward /auth/me to the api server"
    assert all(
        not r.headers.get("x-api-key") and not r.headers.get("authorization")
        for r in me_unauth_hops
    ), "web tier injected a service api_key onto unauthenticated /auth/me"

    # The same exposure on proxied DATA endpoints (/api/* incl. /api/v1/admin/*),
    # NOT covered by the old bc610d8 carve-out, is now closed: unauth => 401, no
    # injected key. (GET /admin/<page> is a public SPA HTML shell, not a data hop.)
    # PDS-009: the roles DATA endpoint the SPA roles page fetches (/api/v1/admin/roles)
    # stays a verbatim caller-auth proxy — unauthenticated => 401, no injected key —
    # so serving the SPA shell at /admin/roles does NOT weaken data auth.
    unsafe_data_paths = ("/api/config", "/api/v1/admin/users", "/api/v1/admin/roles")
    for unsafe_path in unsafe_data_paths:
        resp = client.get(unsafe_path)
        assert resp.status_code == 401, f"{unsafe_path}: {resp.status_code}"
    forwarded_unsafe = [r for r in captured_requests if r.url.path in set(unsafe_data_paths)]
    assert forwarded_unsafe
    assert all(not r.headers.get("x-api-key") for r in forwarded_unsafe)

    # A real caller credential is forwarded verbatim (authenticated path still works).
    me_authed = client.get("/auth/me", headers={"x-api-key": "caller-supplied-key"})
    assert me_authed.status_code == 200
    authed_hops = [r for r in captured_requests if r.url.path == "/auth/me" and r.headers.get("x-api-key")]
    assert authed_hops and all(r.headers.get("x-api-key") == "caller-supplied-key" for r in authed_hops)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


def test_web_tool_proxy_cookie_role_gates_api_forward(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyConfig:
        def get(self, key: str, default: object = None) -> object:
            values = {
                "index.ui.auth_mode": "cookie",
                "index.auth.api_keys": "reader-key:reader,service-admin-key:admin",
            }
            return values.get(key, default)

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

    captured_api_tool_requests: list[httpx.Request] = []

    def _upstream_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/me":
            cookie = request.headers.get("cookie", "")
            if "signed-admin-cookie" in cookie:
                return httpx.Response(
                    200,
                    json={
                        "user": {
                            "id": "admin-user",
                            "roles": ["admin"],
                            "permissions": ["*"],
                        }
                    },
                )
            if request.headers.get("cookie"):
                return httpx.Response(
                    200,
                    json={
                        "user": {
                            "id": "read-only",
                            "roles": ["read-only"],
                            "permissions": ["collection.read"],
                        }
                    },
                )
            return httpx.Response(401, json={"detail": "Authentication failed"})
        if request.url.path == "/api/v1/tools/ingest_text":
            captured_api_tool_requests.append(request)
            cookie = request.headers.get("cookie", "")
            if "signed-admin-cookie" in cookie:
                return httpx.Response(200, json={"job_id": "should-not-run"})
            if cookie:
                return httpx.Response(
                    403,
                    json={"detail": "Authorisation failed for tool 'ingest_text'"},
                )
            return httpx.Response(401, json={"detail": "Authentication failed"})
        return httpx.Response(404, json={"detail": "unexpected path"})

    _mock_transport = httpx.MockTransport(_upstream_handler)
    _real_async_client = web_server.httpx.AsyncClient

    def _mock_async_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = _mock_transport
        return _real_async_client(*args, **kwargs)

    monkeypatch.setattr(web_server.httpx, "AsyncClient", _mock_async_client)

    client = TestClient(web_server.build_web_app())
    anon_write = client.post(
        "/api/v1/tools/ingest_text",
        json={
            "profile": "default",
            "collection": "ut_public_web_proxy",
            "text": "anonymous write must default deny",
            "source": "file://unit/public-web-proxy-anon.txt",
        },
    )

    assert anon_write.status_code == 401
    assert anon_write.json() == {"detail": "Authentication failed"}
    assert len(captured_api_tool_requests) == 1
    assert not captured_api_tool_requests[-1].headers.get("x-api-key")

    client.cookies.set("index_web_session", "signed-read-only-cookie")
    read_only_write = client.post(
        "/api/v1/tools/ingest_text",
        headers={"x-api-key": "valid-admin-token"},
        json={
            "profile": "default",
            "collection": "ut_public_web_proxy",
            "text": "read-only cookie must not borrow or be upgraded by service/admin keys",
            "source": "file://unit/public-web-proxy.txt",
        },
    )

    assert read_only_write.status_code == 403
    assert read_only_write.json() == {"detail": "Authorisation failed for tool 'ingest_text'"}
    assert len(captured_api_tool_requests) == 2
    assert captured_api_tool_requests[-1].headers.get("x-api-key") == "valid-admin-token"

    client.cookies.set("index_web_session", "signed-admin-cookie")
    admin_write = client.post(
        "/api/v1/tools/ingest_text",
        json={
            "profile": "default",
            "collection": "ut_public_web_proxy",
            "text": "admin cookie forwards to the api tool surface",
            "source": "file://unit/public-web-proxy-admin.txt",
        },
    )

    assert admin_write.status_code == 200
    assert admin_write.json() == {"job_id": "should-not-run"}
    assert len(captured_api_tool_requests) == 3
    assert not captured_api_tool_requests[-1].headers.get("x-api-key")
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


def test_requires_caller_auth_locks_identity_bearing_paths() -> None:
    """W28A-734-R2 negative-auth guard: every identity/auth/admin/api path MUST be
    forwarded verbatim (no injected service api_key). Re-narrowing this set is the
    bc610d8 partial-fix mistake that left /auth/me an anonymous-admin bypass."""
    must_be_verbatim = (
        "/auth/me",
        "/auth/login",
        "/auth/logout",
        "/me",
        "/admin/users",
        "/admin/roles",
        "/admin/groups",
        "/admin/api-keys",
        "/admin/rbac",
        "/admin/profiles",
        "/api/config",
        "/api/v1/health",
        "/api/v1/admin/users",
    )
    for path in must_be_verbatim:
        assert web_server._requires_caller_auth(path), f"identity path not protected: {path}"

    # Non-identity static paths keep the canonical WebApiProxy hop.
    for path in ("/app/index.html", "/openapi.json", "/health", "/status"):
        assert not web_server._requires_caller_auth(path), f"static path wrongly forced verbatim: {path}"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-001")


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
