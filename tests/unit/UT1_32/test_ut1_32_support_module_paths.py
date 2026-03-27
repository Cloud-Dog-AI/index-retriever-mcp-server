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
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cloud_dog_logging.audit_schema import Actor, Target
from sqlalchemy.exc import OperationalError

from index_tools.audit.logger import AuditLogger
from index_tools.collections.manager import CollectionManager
from index_tools.collections.schema import CollectionSchema
from index_tools.config.loader import bind_model, get_config
from index_tools.connectors import ftp, gdrive, http, s3, webdav
from index_tools.connectors.filesystem import resolve as filesystem_resolve
from index_tools.connectors.models import FetchPlan
from index_tools.convert import deepdoc, mineru, pandoc
from index_tools.lifecycle.retention import older_than_days
from index_tools.pipeline.chunking import paragraph_chunks, token_chunks
from index_tools.queue import engine as queue_engine_module
from index_tools.queue.engine import QueueEngine
from index_tools.queue.models import JobRecord, JobStatus
from index_tools.queue.redis_bridge import RedisBridge
from index_tools.search.reranker import rerank_by_score
from index_tools.security import rbac as rbac_module
from index_tools.security.rbac import RbacAuthoriser, Subject
from index_tools.security.scope import ScopeError, validate_uri
from index_tools.tools.definitions import SearchInput
from index_tools.tools.handlers import handle_ingest_text, handle_search
from tests.unit.helpers import minimal_config


def test_collection_schema_and_fetch_plan_defaults() -> None:
    schema = CollectionSchema(name="alpha", dimension=4)
    assert schema.distance_metric == "cosine"
    plan = FetchPlan(source_type="x", location="y")
    assert plan.metadata == {}


def test_connectors_and_converters_paths(tmp_path: Path) -> None:
    file_path = tmp_path / "a.txt"
    file_path.write_text("alpha", encoding="utf-8")

    fs = filesystem_resolve([str(tmp_path)], str(file_path))
    assert fs.source_type == "filesystem"

    assert ftp.resolve("ftp://example.com/doc.txt").metadata["host"] == "example.com"
    assert http.resolve("https://example.com/doc.txt").metadata["host"] == "example.com"
    assert gdrive.resolve("file123").metadata["file_id"] == "file123"
    assert s3.resolve("s3://bucket/key").metadata["bucket"] == "bucket"
    assert webdav.resolve("https://dav.example.com/file").metadata["host"] == "dav.example.com"

    with pytest.raises(ValueError):
        ftp.resolve("http://bad")
    with pytest.raises(ValueError):
        http.resolve("ftp://bad")
    with pytest.raises(ValueError):
        gdrive.resolve(" ")

    assert deepdoc.available() is False
    assert mineru.available() is False
    assert pandoc.convert(b"\xff") == "\ufffd"


def test_lifecycle_chunking_scope_and_rerank() -> None:
    old = datetime.now(timezone.utc) - timedelta(days=20)  # noqa: UP017
    new = datetime.now(timezone.utc)  # noqa: UP017
    assert older_than_days(old, 10) is True
    assert older_than_days(new, 10) is False

    assert paragraph_chunks("a\n\nb\n\n\nc") == ["a", "b", "c"]
    assert token_chunks("a b c d", chunk_size=2, chunk_overlap=1) == ["a b", "b c", "c d"]
    with pytest.raises(ValueError):
        token_chunks("a", chunk_size=0, chunk_overlap=0)
    with pytest.raises(ValueError):
        token_chunks("a", chunk_size=2, chunk_overlap=2)

    validate_uri("https://example.com/a", {"https"}, {"example.com"})
    with pytest.raises(ScopeError):
        validate_uri("ftp://example.com/a", {"https"})
    with pytest.raises(ScopeError):
        validate_uri("https://blocked.example/a", {"https"}, {"example.com"})

    ranked = rerank_by_score([{"score": "1.0"}, {"score": 5}, {"score": object()}])
    assert [row["score"] for row in ranked[:2]] == [5, "1.0"]


def test_queue_engine_and_redis_bridge_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = QueueEngine(database_url=f"sqlite+aiosqlite:///{tmp_path / 'ut1_32_jobs.db'}", server_id="ut1-32")
    job = JobRecord(job_id="j1", profile="default", collection="c", job_type="ingest_text", idempotency_key="k")
    engine.enqueue(job)

    assert engine.generate_idempotency_key("p", "c", "s")
    assert engine.get("j1").job_id == "j1"
    assert len(engine.list_jobs()) == 1

    run_job = engine.run("j1", lambda _: None)
    assert run_job.status is JobStatus.succeeded

    failing = JobRecord(job_id="j2", profile="default", collection="c", job_type="ingest_text", idempotency_key="k2")
    engine.enqueue(failing)
    with pytest.raises(RuntimeError):
        engine.run("j2", lambda _: (_ for _ in ()).throw(RuntimeError("boom")))
    assert engine.get("j2").status is JobStatus.failed

    assert engine.backend_name() == "cloud_dog_jobs"
    monkeypatch.setattr(queue_engine_module, "cloud_dog_jobs", None)
    with pytest.raises(RuntimeError, match="cloud_dog_jobs is required"):
        QueueEngine(database_url=f"sqlite+aiosqlite:///{tmp_path / 'ut1_32_jobs_missing.db'}", server_id="ut1-32-missing")
    monkeypatch.setattr(queue_engine_module, "cloud_dog_jobs", object())

    assert RedisBridge(enabled=False).status() == "disabled"
    assert RedisBridge(enabled=True, url="redis://local").status() == "enabled"


def test_queue_engine_recovers_from_existing_table_startup_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class DummyBackend:
        def __init__(self, database_url: str) -> None:
            calls.append(database_url)
            if len([entry for entry in calls if str(entry).startswith("sqlite:")]) == 1:
                raise OperationalError("CREATE TABLE job_callbacks", {}, Exception("table job_callbacks already exists"))
            self.database_url = database_url

    monkeypatch.setattr(queue_engine_module, "_ensure_sqlite_queue_schema", lambda database_url: calls.append("ensure"))
    monkeypatch.setattr(queue_engine_module, "SQLQueueBackend", DummyBackend)
    monkeypatch.setattr(queue_engine_module, "JobQueue", lambda backend: {"backend": backend})
    monkeypatch.setattr(queue_engine_module, "cloud_dog_jobs", object())

    engine = QueueEngine(database_url="sqlite+aiosqlite:////tmp/ut1_32_existing.db", server_id="ut1-32-existing")

    assert calls == [
        "ensure",
        "sqlite:////tmp/ut1_32_existing.db",
        "ensure",
        "sqlite:////tmp/ut1_32_existing.db",
    ]
    assert engine.backend_name() == "cloud_dog_jobs"


def test_audit_logger_backend_name_and_write(tmp_path: Path) -> None:
    out = tmp_path / "audit.jsonl"
    logger = AuditLogger(path=out, server_id="ut-audit")
    event = logger.build_event(
        event_type="tool.call",
        actor=Actor(type="user", id="tester", roles=["writer"]),
        action="execute",
        outcome="success",
        target=Target(type="collection", id="c", name="c"),
        details={"api_key": "secret", "nested": {"password": "x"}},
    )
    logger.write_event(event)
    content = out.read_text(encoding="utf-8")
    assert "REDACTED" in content
    assert '"service_instance": "ut-audit"' in content
    assert '"correlation_id":' in content
    assert '"environment":' in content
    assert '"actor": {"type": "user", "id": "tester", "roles": ["writer"]}' in content
    assert logger.get_backend_name() == "cloud_dog_logging"


def test_audit_logger_admin_and_security_helpers(tmp_path: Path) -> None:
    out = tmp_path / "audit-admin.jsonl"
    logger = AuditLogger(path=out, server_id="ut-admin")

    logger.log_admin_action(
        actor="admin-user",
        roles={"admin"},
        action="create",
        target_type="profile",
        target_id="alpha",
        new_value={"enabled": True},
    )
    logger.log_security_event(
        actor="reader-user",
        action="authenticate",
        target_type="endpoint",
        target_id="/admin/profiles",
        outcome="success",
        roles={"reader"},
        ip="127.0.0.1",
        user_agent="pytest",
        auth_mechanism="api_key",
    )

    rows = out.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2
    admin_row, auth_row = rows
    assert '"event_type": "admin.create"' in admin_row
    assert '"service_instance": "ut-admin"' in admin_row
    assert '"correlation_id":' in admin_row
    assert '"target": {"type": "profile", "id": "alpha"}' in admin_row
    assert '"event_type": "security.authenticate"' in auth_row
    assert '"ip": "127.0.0.1"' in auth_row
    assert '"user_agent": "pytest"' in auth_row


def test_audit_logger_security_helper_supports_legacy_actor_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    out = tmp_path / "audit-legacy-actor.jsonl"
    logger = AuditLogger(path=out, server_id="ut-legacy")
    captured: dict[str, object] = {}

    class LegacyActor:
        def __init__(self, *, type: str, id: str, roles: list[str] | None = None) -> None:
            self.type = type
            self.id = id
            self.roles = roles

    def capture_log_security(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("index_tools.audit.logger.Actor", LegacyActor)
    monkeypatch.setattr(logger._platform, "log_security", capture_log_security)

    logger.log_security_event(
        actor="reader-user",
        action="authenticate",
        target_type="endpoint",
        target_id="/a2a/health",
        outcome="success",
        roles={"reader"},
        ip="127.0.0.1",
        user_agent="pytest",
        auth_mechanism="api_key",
    )

    actor = captured["actor"]
    assert isinstance(actor, LegacyActor)
    assert actor.id == "reader-user"
    assert actor.roles == ["reader"]
    assert captured["outcome"] == "success"


def test_audit_logger_security_helper_supports_legacy_target_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    out = tmp_path / "audit-legacy-target.jsonl"
    logger = AuditLogger(path=out, server_id="ut-legacy-target")
    captured: dict[str, object] = {}

    class LegacyTarget:
        def __init__(self, *, type: str, id: str) -> None:
            self.type = type
            self.id = id

    def capture_log_security(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("index_tools.audit.logger.Target", LegacyTarget)
    monkeypatch.setattr(logger._platform, "log_security", capture_log_security)

    logger.log_security_event(
        actor="reader-user",
        action="authenticate",
        target_type="endpoint",
        target_id="/a2a/health",
        outcome="success",
        roles={"reader"},
        auth_mechanism="api_key",
    )

    target = captured["target"]
    assert isinstance(target, LegacyTarget)
    assert target.type == "endpoint"
    assert target.id == "/a2a/health"


def test_rbac_backend_name_and_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    auth = RbacAuthoriser(role_actions={"writer": ["ingest_*"]}, default_deny=True)
    subject = Subject(user_id="u1", roles={"writer"})
    assert auth.is_allowed(subject, "ingest_text") is True
    assert auth.is_allowed(subject, "delete_by_id") is False

    permissive = RbacAuthoriser(role_actions={}, default_deny=False)
    assert permissive.is_allowed(Subject(user_id="u2", roles={"x"}), "anything") is True

    monkeypatch.setattr(rbac_module, "cloud_dog_idam", None)
    assert auth.backend_name() == "fallback"
    monkeypatch.setattr(rbac_module, "cloud_dog_idam", object())
    assert auth.backend_name() == "cloud_dog_idam"


def test_handlers_and_config_paths() -> None:
    payload = SearchInput(profile="default", collection="c", query="q", top_k=3)
    out = handle_search(
        payload,
        search_fn=lambda **_: [
            {"doc_id": "d1", "chunk_id": "c1", "text": "x", "score": 0.5, "metadata": {}},
        ],
    )
    assert out.results[0].doc_id == "d1"
    assert handle_ingest_text().status == "queued"

    cfg = minimal_config()
    model = bind_model(cfg)
    assert model.api_server.port == int(os.environ["CLOUD_DOG__API_SERVER__PORT"])
    assert model.web_server.port == int(os.environ["CLOUD_DOG__WEB_SERVER__PORT"])
    assert model.mcp_server.port == int(os.environ["CLOUD_DOG__MCP_SERVER__PORT"])
    assert model.a2a_server.port == int(os.environ["CLOUD_DOG__A2A_SERVER__PORT"])
    merged_port = int(os.environ["CLOUD_DOG__API_SERVER__PORT"]) + 9
    merged = get_config(defaults_layer=minimal_config(), config_layer={"api_server": {"port": merged_port}})
    assert merged.api_server.port == merged_port

    manager = CollectionManager()
    manager.create("alpha")
    assert manager.list() == ["alpha"]
    manager.delete("alpha")
    assert manager.list() == []
