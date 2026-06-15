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
from index_server.logging_runtime import build_platform_log_config
from tests.unit.helpers import minimal_config
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_collection_schema_and_fetch_plan_defaults() -> None:
    schema = CollectionSchema(name="alpha", dimension=4)
    assert schema.distance_metric == "cosine"
    plan = FetchPlan(source_type="x", location="y")
    assert plan.metadata == {}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


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
    assert engine.get("j2").status is JobStatus.dead_lettered

    assert engine.backend_name() == "cloud_dog_jobs"
    monkeypatch.setattr(queue_engine_module, "cloud_dog_jobs", None)
    with pytest.raises(RuntimeError, match="cloud_dog_jobs is required"):
        QueueEngine(database_url=f"sqlite+aiosqlite:///{tmp_path / 'ut1_32_jobs_missing.db'}", server_id="ut1-32-missing")
    monkeypatch.setattr(queue_engine_module, "cloud_dog_jobs", object())

    assert RedisBridge(enabled=False).status() == "disabled"
    assert RedisBridge(enabled=True, url="redis://local").status() == "enabled"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


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
    payload = json.loads(content)
    assert "REDACTED" in content
    assert '"service_instance": "ut-audit"' in content
    assert '"correlation_id":' in content
    assert '"environment":' in content
    assert payload["actor"]["type"] == "user"
    assert payload["actor"]["id"] == "tester"
    assert payload["actor"]["roles"] == ["writer"]
    assert logger.get_backend_name() == "cloud_dog_logging"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_audit_logger_ingest_helper_emits_schema_complete_tool_event(tmp_path: Path) -> None:
    out = tmp_path / "audit-ingest.jsonl"
    logger = AuditLogger(path=out, server_id="ut-ingest")

    logger.log_ingest(
        actor="writer-user",
        profile="default",
        collection="docs",
        job_id="job-1",
        source="upload",
        metadata={"token": "secret"},
        chunk_count=4,
        document_count=2,
    )

    row = out.read_text(encoding="utf-8")
    assert '"event_type": "tool.call"' in row
    assert '"action": "execute"' in row
    assert '"target": {"type": "tool", "id": "ingest_text", "name": "ingest_text"}' in row
    assert '"actor": {"type": "user", "id": "writer-user"' in row
    assert '"metadata": {"token": "***REDACTED***"}' in row
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_audit_logger_admin_helper_falls_back_when_privileged_api_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    out = tmp_path / "audit-admin-fallback.jsonl"
    logger = AuditLogger(path=out, server_id="ut-admin-fallback")
    captured: dict[str, object] = {}

    def capture_log_crud(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logger._platform, "log_privileged", None, raising=False)
    monkeypatch.setattr(logger._platform, "log_crud", capture_log_crud)

    logger.log_admin_action(
        actor="admin-user",
        roles={"admin"},
        action="create",
        target_type="profile",
        target_id="alpha",
        new_value={"enabled": True},
    )

    assert captured["action"] == "create"
    assert captured["outcome"] == "success"
    assert captured["server_id"] == "ut-admin-fallback"
    assert captured["new_value"] == {"enabled": True}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_audit_logger_build_event_supports_legacy_audit_event_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    out = tmp_path / "audit-legacy-event.jsonl"
    logger = AuditLogger(path=out, server_id="ut-legacy-event")

    class LegacyAuditEvent:
        def __init__(
            self,
            *,
            event_type: str,
            actor: object,
            action: str,
            outcome: str,
            correlation_id: str,
            service: str,
            timestamp: str = "",
            target: object | None = None,
            details: dict[str, object] | None = None,
            duration_ms: int | None = None,
        ) -> None:
            self.event_type = event_type
            self.actor = actor
            self.action = action
            self.outcome = outcome
            self.correlation_id = correlation_id
            self.service = service
            self.timestamp = timestamp
            self.target = target
            self.details = details
            self.duration_ms = duration_ms

    monkeypatch.setattr("index_tools.audit.logger.AuditEvent", LegacyAuditEvent)

    event = logger.build_event(
        event_type="tool.call",
        actor=Actor(type="user", id="tester"),
        action="execute",
        outcome="success",
        target=Target(type="collection", id="c"),
        details={"password": "secret"},
    )

    assert isinstance(event, LegacyAuditEvent)
    assert event.service == "index-retriever-mcp-server"
    assert event.details == {"password": "[REDACTED]"}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_build_platform_log_config_uses_surface_specific_log_files() -> None:
    class DummyConfig:
        def __init__(self, values: dict[str, object]) -> None:
            self._values = values

        def get(self, key: str, default: object | None = None) -> object | None:
            return self._values.get(key, default)

    config = DummyConfig(
        {
            "service.name": "index-retriever-mcp-server",
            "log.service_instance": "ut-index-instance",
            "log.environment": "test",
            "log.level": "INFO",
            "log.format": "json",
            "log.console": True,
            "log.audit_log": "logs/audit.log.jsonl",
            "log.api_server_log": "logs/api_server.log",
            "log.web_server_log": "logs/web_server.log",
            "log.mcp_server_log": "logs/mcp_server.log",
            "log.a2a_server_log": "logs/a2a_server.log",
            "log.rotation.mode": "size",
            "log.rotation.max_bytes": 1234,
            "log.rotation.backup_count": 2,
            "log.rotation.when": "midnight",
            "log.rotation.interval": 1,
            "log.rotation.compress": True,
            "log.integrity.enabled": True,
            "log.integrity.interval_seconds": 300,
            "log.integrity.log_file": "logs/audit-integrity.log",
            "log.integrity.hash_algorithm": "sha256",
            "log.retention.hot_days": 14,
            "log.retention.cold_days": 60,
            "log.retention.archive_format": "gz",
        }
    )

    payload = build_platform_log_config(config, surface_name="web_server")

    assert payload["service_name"] == "index-retriever-mcp-server"
    assert payload["service_instance"] == "ut-index-instance"
    assert payload["environment"] == "test"
    assert payload["log"]["app_log"] == "logs/web_server.log"
    assert payload["log"]["audit_log"] == "logs/audit.log.jsonl"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_rbac_backend_name_and_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    auth = RbacAuthoriser(role_permissions={"user": ["collection.write"]}, default_deny=True)
    subject = Subject(user_id="u1", roles={"user"})
    assert auth.is_allowed(subject, "collection.write") is True
    assert auth.is_allowed(subject, "admin") is False

    permissive = RbacAuthoriser(role_permissions={}, default_deny=False)
    assert permissive.is_allowed(Subject(user_id="u2", roles={"x"}), "collection.read") is True

    # W28A-703: fallback removed — cloud_dog_idam is now a hard requirement.
    # Backend name always returns "cloud_dog_idam".
    assert auth.backend_name() == "cloud_dog_idam"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_handlers_and_config_paths() -> None:
    api_port = int(os.environ.get("CLOUD_DOG__API_SERVER__PORT", "8074"))
    web_port = int(os.environ.get("CLOUD_DOG__WEB_SERVER__PORT", "8075"))
    mcp_port = int(os.environ.get("CLOUD_DOG__MCP_SERVER__PORT", "8076"))
    a2a_port = int(os.environ.get("CLOUD_DOG__A2A_SERVER__PORT", "8077"))
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
    assert model.api_server.port == api_port
    assert model.web_server.port == web_port
    assert model.mcp_server.port == mcp_port
    assert model.a2a_server.port == a2a_port
    merged_port = api_port + 9
    merged = get_config(defaults_layer=minimal_config(), config_layer={"api_server": {"port": merged_port}})
    assert merged.api_server.port == merged_port

    manager = CollectionManager()
    manager.create("alpha")
    assert manager.list() == ["alpha"]
    manager.delete("alpha")
    assert manager.list() == []
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_db_runtime_serialises_sqlite_migrations_and_retries_existing_table(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from index_tools.db import runtime as db_runtime_module

    calls: list[str] = []
    lock_paths: list[str] = []

    class DummyLock:
        def __init__(self, path: str) -> None:
            lock_paths.append(path)

        def __enter__(self) -> None:
            return None

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    class DummyRunner:
        def upgrade(self, revision: str) -> None:
            calls.append(revision)
            if len(calls) == 1:
                raise OperationalError(
                    "CREATE TABLE index_platform_db_state",
                    {},
                    Exception("table index_platform_db_state already exists"),
                )

    monkeypatch.setattr(db_runtime_module, "FileLock", DummyLock)

    runner = DummyRunner()
    sqlite_path = tmp_path / "runtime.db"

    db_runtime_module._run_migrations(runner, sqlite_path)

    assert calls == ["head", "head"]
    assert lock_paths == [f"{sqlite_path}.migrate.lock"]
