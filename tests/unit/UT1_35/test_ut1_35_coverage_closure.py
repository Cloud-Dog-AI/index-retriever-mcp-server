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

import asyncio
import runpy
import sys
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from index_server import api_server, mcp_server
from index_server.auth import middleware as auth_middleware_mod
from index_server.auth.middleware import AuthMiddleware, AuthResult
from index_tools.connectors import filesystem, s3, webdav
from index_tools.connectors.models import FetchPlan
from index_tools.convert.registry import ConverterRegistry
from index_tools.embeddings import adapter as embedding_adapter_mod
from index_tools.embeddings.adapter import EmbeddingAdapter
from index_tools.embeddings.registry import EmbeddingRegistry
from index_tools.pipeline import dedupe as dedupe_mod
from index_tools.pipeline.chunking import token_chunks
from index_tools.pipeline.dedupe import DedupeIndex, DedupeRecord
from index_tools.security.rbac import RbacAuthoriser, Subject
from index_tools.tools.definitions import GenericToolInput, GenericToolOutput
from index_tools.tools.registry import ToolRegistry, ToolSpec
from index_tools.vdb.registry import VdbRegistry
from tests.http_paths import api_tools_path


class _DummyService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def search(self, **kwargs):
        self.calls.append(("search", kwargs))
        return [{"doc_id": "d1"}]

    def ingest_text(self, **kwargs):
        self.calls.append(("ingest_text", kwargs))
        return "job-123"

    def backend_health_check(self):
        return {"status": "ok"}

    def embedding_health_check(self):
        return {"status": "ok", "dimensions": 8}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # W28C-1711-R3.5 invalid-binding archived (FR-017)


def test_api_middleware_helpers_and_handler_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: FR-17
    app = SimpleNamespace(user_middleware=[], build_middleware_stack=lambda: "noop", middleware_stack=None)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("TEST_ENV_TIER", "IT")
    assert api_server._maybe_disable_timeout_middleware(app) is app

    marker = SimpleNamespace(cls=SimpleNamespace(__name__="OtherMiddleware"))
    app2 = SimpleNamespace(user_middleware=[marker], build_middleware_stack=lambda: "stack", middleware_stack=None)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "ut")
    assert api_server._maybe_disable_timeout_middleware(app2) is app2
    assert app2.middleware_stack is None

    service = _DummyService()

    class _Auth:
        def identity_from_headers(self, _headers):
            return AuthResult(
                user_id="u1",
                roles={"user"},
                permissions={"collection.read", "collection.write"},
                token_type="api_key",
            )

        def require_permission(self, _identity, _allowed):
            return None

    result = api_server.handle_search(
        service=service,  # type: ignore[arg-type]
        auth=_Auth(),  # type: ignore[arg-type]
        headers={},
        payload={"profile": "default", "collection": "c1", "query": "alpha", "top_k": 2, "filters": {"k": "v"}},
    )
    assert result["results"][0]["doc_id"] == "d1"

    queued = api_server.handle_ingest_text(
        service=service,  # type: ignore[arg-type]
        auth=_Auth(),  # type: ignore[arg-type]
        headers={},
        payload={"profile": "default", "collection": "c1", "text": "payload"},
    )
    assert queued == {"job_id": "job-123"}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # W28C-1711-R3.5 invalid-binding archived (FR-017)


def test_api_require_permission_http403_branch(monkeypatch: pytest.MonkeyPatch, service) -> None:
    monkeypatch.setattr(
        AuthMiddleware,
        "require_permission",
        staticmethod(lambda _identity, _allowed: (_ for _ in ()).throw(PermissionError("denied"))),
    )
    app = api_server.build_api_app(service=service)
    client = TestClient(app)
    local_health = client.get("/health")
    assert local_health.status_code == 200
    assert local_health.json()["status"] == "ok"
    response = client.get(api_tools_path(), headers={"x-api-key": "test-api-key"})
    assert response.status_code == 403
    assert "denied" in response.text
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # W28C-1711-R3.5 invalid-binding archived (FR-017)


def test_api_main_module_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    api_port = os.environ.get("CLOUD_DOG__API_SERVER__PORT", "8074")
    captured: dict[str, object] = {}
    fake_uvicorn = SimpleNamespace(
        run=lambda app, host, port, log_level: captured.update(
            {"app": app, "host": host, "port": port, "log_level": log_level}
        )
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setenv("CLOUD_DOG__API_SERVER__PORT", api_port)
    runpy.run_module("index_server.api_server", run_name="__main__", alter_sys=True)
    assert captured["port"] == int(api_port)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # W28C-1711-R3.5 invalid-binding archived (FR-017)


def test_mcp_role_mapping_and_execute_paths(service, monkeypatch: pytest.MonkeyPatch) -> None:
    assert mcp_server._required_permission_for_tool("admin_any") == "admin"
    assert mcp_server._required_permission_for_tool("delete_by_id") == "collection.write"
    assert mcp_server._required_permission_for_tool("unknown_anything") == "admin"

    marker = SimpleNamespace(cls=SimpleNamespace(__name__="OtherMiddleware"))
    app = SimpleNamespace(user_middleware=[marker], build_middleware_stack=lambda: "stack", middleware_stack=None)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("TEST_ENV_TIER", "IT")
    assert mcp_server._maybe_disable_timeout_middleware(app) is app
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "ut")
    assert mcp_server._maybe_disable_timeout_middleware(app) is app

    assert "default" in mcp_server.execute_tool(service, "profiles_list", {}, identity_roles={"admin"})["profiles"]
    assert "profile" in mcp_server.execute_tool(
        service, "profile_get", {"profile": "default"}, identity_roles={"admin"}
    )
    assert "collections" in mcp_server.execute_tool(
        service, "collections_list", {"profile": "default"}, identity_roles={"admin"}
    )
    assert (
        mcp_server.execute_tool(
            service,
            "admin_collection_create",
            {"profile": "default", "collection": "mcp_cov"},
            identity_roles={"admin"},
        )["status"]
        == "ok"
    )
    assert (
        mcp_server.execute_tool(
            service,
            "admin_collection_delete",
            {"profile": "default", "collection": "mcp_cov"},
            identity_roles={"admin"},
        )["status"]
        == "ok"
    )
    assert (
        mcp_server.execute_tool(
            service,
            "ingest_text",
            {"profile": "default", "collection": "mcp_cov", "text": "payload"},
            identity_roles={"admin"},
        )["status"]
        == "queued"
    )
    assert "results" in mcp_server.execute_tool(
        service,
        "search",
        {"profile": "default", "collection": "mcp_cov", "query": "payload"},
        identity_roles={"admin"},
    )

    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="admin_profile_update", input_model=GenericToolInput, output_model=GenericToolOutput)
    )
    assert mcp_server.execute_tool(
        service,
        "admin_profile_update",
        {"profile": "default"},
        registry=registry,
        identity_roles={"admin"},
    ) == {"status": "ok"}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # W28C-1711-R3.5 invalid-binding archived (FR-017)


def test_mcp_health_and_main_module_paths(monkeypatch: pytest.MonkeyPatch, service) -> None:
    mcp_port = os.environ.get("CLOUD_DOG__MCP_SERVER__PORT", "8076")
    app = mcp_server.build_mcp_app(service=service)
    local_health = next(
        route.endpoint
        for route in app.router.routes
        if getattr(route, "path", "") == "/health"
    )
    health_payload = asyncio.run(local_health())
    assert health_payload["status"] == "ok"
    assert health_payload["application"] == "index-retriever-mcp-server"

    captured: dict[str, object] = {}
    fake_uvicorn = SimpleNamespace(
        run=lambda app, host, port, log_level: captured.update(
            {"app": app, "host": host, "port": port, "log_level": log_level}
        )
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setenv("CLOUD_DOG__MCP_SERVER__PORT", mcp_port)
    runpy.run_module("index_server.mcp_server", run_name="__main__", alter_sys=True)
    assert captured["port"] == int(mcp_port)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # W28C-1711-R3.5 invalid-binding archived (FR-017)


def test_auth_connector_registry_and_embedding_branches(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(auth_middleware_mod, "cloud_dog_idam", None)
    with pytest.raises(RuntimeError, match="cloud_dog_idam is required"):
        AuthMiddleware()

    payload = tmp_path / "payload.txt"
    payload.write_text("content", encoding="utf-8")
    data = filesystem.fetch(FetchPlan(source_type="filesystem", location=str(payload), metadata={}))
    assert data == b"content"
    with pytest.raises(ValueError):
        s3.resolve("http://bad-s3-uri")
    with pytest.raises(ValueError):
        webdav.resolve("ftp://bad-webdav-uri")

    converters = ConverterRegistry()
    converters.register("*", lambda raw: raw.decode("utf-8"))
    assert converters.select(".missing")(b"x") == "x"
    converters = ConverterRegistry()
    with pytest.raises(KeyError):
        converters.select(".missing")

    providers = EmbeddingRegistry()
    with pytest.raises(KeyError):
        providers.get("unknown")

    class _EmbedModule:
        @staticmethod
        def embed(provider: str, model: str, inputs: list[str]) -> list[list[float]]:
            return [[float(len(provider)), float(len(model)), float(len(inputs[0]))]]

    monkeypatch.setattr(embedding_adapter_mod, "cloud_dog_llm", _EmbedModule())
    adapter = EmbeddingAdapter(provider="ollama", model="nomic")
    assert adapter.embed(["abc"])[0][2] == 3.0
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # W28C-1711-R3.5 invalid-binding archived (FR-017)


def test_chunking_dedupe_rbac_and_vdb_registry_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    assert token_chunks("", chunk_size=4, chunk_overlap=1) == []

    class _WeirdTokens:
        def __len__(self) -> int:
            return 3

        def __getitem__(self, _key):
            return []

    class _WeirdText:
        def split(self):
            return _WeirdTokens()

    assert token_chunks(_WeirdText(), chunk_size=2, chunk_overlap=1) == []  # type: ignore[arg-type]

    class _Digest:
        @staticmethod
        def hexdigest() -> str:
            return "xxhash-value"

    class _XXHash:
        @staticmethod
        def xxh64(_content: bytes) -> _Digest:
            return _Digest()

    monkeypatch.setattr(dedupe_mod, "xxhash_module", _XXHash())
    index = DedupeIndex()
    assert index.fingerprint(b"abc", method="xxhash") == "xxhash-value"

    existing = DedupeRecord(doc_id="a", size=1, mtime=1, fingerprint="f1")
    index.upsert(existing)
    assert index.check_duplicate(DedupeRecord(doc_id="b", size=2, mtime=2, fingerprint="f2"), mode="size+mtime") is None
    assert index.check_duplicate(DedupeRecord(doc_id="c", size=3, mtime=3, fingerprint="f3"), mode="hash") is None
    assert index.apply_policy(None, "skip") == "ingest"
    with pytest.raises(ValueError):
        index.apply_policy(existing, "bad-policy")

    rbac = RbacAuthoriser(role_permissions={"viewer": ["collection.read"]}, default_deny=True)
    assert rbac.is_allowed(Subject(user_id="u", roles={"viewer"}), "collection.read") is True

    registry = VdbRegistry()
    with pytest.raises(KeyError):
        registry.get("unknown")
