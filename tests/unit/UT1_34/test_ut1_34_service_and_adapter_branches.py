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
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from index_tools.search.engine import SearchEngine, validate_filters
from index_tools.tools.service import IndexService
from index_tools.vdb.adapters import InMemoryVdbAdapter
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_service_collection_and_admin_paths(service: IndexService) -> None:
    service.admin_collection_create("default", "keep", roles={"admin"})
    service.collection_manager.create("other:skip")
    assert service.collections_list("default") == ["keep"]

    with pytest.raises(PermissionError):
        service.admin_collection_delete("default", "keep", roles={"writer"})
    service.admin_collection_delete("default", "keep", roles={"admin"})
    assert service.collections_list("default") == []
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_service_collection_create_allows_unregistered_backend_profile(service: IndexService) -> None:
    service.admin_profile_create(
        "missing-backend",
        roles={"admin"},
        config={"backend": "nonexistent-backend", "enabled": True, "roles": ["reader", "writer", "maintainer"]},
        actor="admin",
    )

    service.admin_collection_create(
        "missing-backend",
        "pending",
        roles={"admin"},
        payload={"metadata": {}},
        actor="admin",
    )

    record = service.collection_get("missing-backend", "pending")
    assert record["collection"] == "pending"
    assert record["metadata"]["backend_binding_pending"] is True
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_live_collection_create_marks_pending_without_blocking_backend_create(
    monkeypatch: pytest.MonkeyPatch, service: IndexService
) -> None:
    async def _missing_collection(*_args, **_kwargs):
        return None

    async def _unexpected_create(*_args, **_kwargs):
        raise AssertionError("backend create_collection should not run during live admin collection creation")

    monkeypatch.setattr(service, "_async_job_execution", True)
    monkeypatch.setattr(service.vdb, "get_collection", _missing_collection)
    monkeypatch.setattr(service.vdb, "create_collection", _unexpected_create)

    service.admin_collection_create(
        "default",
        "lazy-live-binding",
        roles={"admin"},
        payload={"metadata": {}},
        actor="admin",
    )

    record = service.collection_get("default", "lazy-live-binding")
    assert record["metadata"]["backend_binding_pending"] is True
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_ingest_text_queues_failed_job_for_unregistered_backend_profile(service: IndexService) -> None:
    service.queue._retry_max_attempts = 1
    service.queue._retry_backoff_seconds = 0.0
    service.admin_profile_create(
        "missing-backend-ingest",
        roles={"admin"},
        config={"backend": "nonexistent-backend", "enabled": True, "roles": ["reader", "writer", "maintainer"]},
        actor="admin",
    )
    service.admin_collection_create(
        "missing-backend-ingest",
        "pending",
        roles={"admin"},
        payload={"metadata": {}},
        actor="admin",
    )

    job_id = service.ingest_text(
        "missing-backend-ingest",
        "pending",
        "queued against missing backend",
        "api://missing-backend-ingest",
        actor="writer",
    )
    job = service.job_wait(job_id)

    assert job.job_id == job_id
    assert str(getattr(job.status, "value", job.status)).lower() in {"failed", "dead_lettered"}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_live_ingest_dispatches_async_when_enabled(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
    started: list[str] = []

    def _capture(job_id: str) -> None:
        started.append(job_id)

    monkeypatch.setattr(service, "_async_job_execution", True)
    monkeypatch.setattr(service, "_dispatch_job_async", _capture)

    job_id = service.ingest_text(
        "default",
        "async-dispatch",
        "async queue payload",
        "api://async-dispatch",
        actor="writer",
    )

    assert started == [job_id]
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_service_idempotency_retrieve_delete_and_retention(
    monkeypatch: pytest.MonkeyPatch, service: IndexService
) -> None:
    first_job_id = service.ingest_text(
        "default",
        "idem",
        "same payload",
        "api://same",
        actor="writer",
        idempotency_key="fixed-key",
    )
    second_job_id = service.ingest_text(
        "default",
        "idem",
        "same payload",
        "api://same",
        actor="writer",
        idempotency_key="fixed-key",
    )
    assert first_job_id == second_job_id

    monkeypatch.setattr("index_tools.tools.service.token_chunks", lambda *_args, **_kwargs: [])
    service.ingest_text("default", "fallback", "single chunk fallback", "api://fallback", actor="writer")
    fallback_doc_id = next(
        doc_id
        for doc_id, payload in service.documents.items()
        if payload.collection == "fallback" and payload.profile == "default"
    )
    doc_payload = service.retrieve(fallback_doc_id)
    assert doc_payload["text"] == "single chunk fallback"
    assert service.delete_by_id("default", "fallback", fallback_doc_id) is True

    old_created = datetime.now(timezone.utc) - timedelta(days=200)  # noqa: UP017
    service.ingest_text(
        "default",
        "retention_cov",
        "old payload",
        "api://retention/old",
        actor="writer",
        created_at=old_created,
    )
    removed = service.retention_run("default", "retention_cov", older_than_days=90)
    assert removed >= 1
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_service_search_wrapper_path(service: IndexService) -> None:
    service.ingest_text("default", "search_cov", "alpha beta gamma", "api://search", actor="writer")
    rows = service.search("default", "search_cov", "alpha", top_k=5, filters=None)
    assert rows
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_service_search_falls_back_to_local_documents_when_vdb_returns_empty(
    monkeypatch: pytest.MonkeyPatch, service: IndexService
) -> None:
    service.ingest_text(
        "default",
        "search_local_fallback",
        "cloud computing fallback document",
        "api://search-local-fallback",
        actor="writer",
        metadata={"tenant": "alpha"},
    )

    async def _empty_search(*_args, **_kwargs):
        return SimpleNamespace(results=[])

    monkeypatch.setattr(service.vdb, "search", _empty_search)

    rows = service.search(
        "default",
        "search_local_fallback",
        "cloud computing",
        top_k=5,
        filters={"tenant": "alpha"},
    )

    assert len(rows) == 1
    assert "cloud computing fallback document" in rows[0]["text"]
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_ingest_uses_backend_collection_name_for_upsert(
    monkeypatch: pytest.MonkeyPatch, service: IndexService
) -> None:
    captured: dict[str, object] = {}

    async def _capture_upsert(collection_name: str, records: list[object], provider_id: str | None = None) -> bool:
        captured["collection_name"] = collection_name
        captured["provider_id"] = provider_id
        captured["records"] = records
        return True

    monkeypatch.setattr(service.vdb, "upsert_records", _capture_upsert)

    service.ingest_text("default", "backend_name_cov", "alpha beta gamma", "api://backend-name", actor="writer")

    provider_id = service._profile_provider("default")
    assert captured["collection_name"] == service._backend_collection_name(
        "default", "backend_name_cov", provider_id=provider_id
    )
    assert captured["collection_name"] != "default:backend_name_cov"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_service_passes_resolved_embedding_settings_into_vdb_client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    def _fake_get_vdb_client(config: dict[str, object]) -> InMemoryVdbAdapter:
        captured["config"] = config
        return InMemoryVdbAdapter()

    monkeypatch.setattr("index_tools.tools.service.get_vdb_client", _fake_get_vdb_client)

    service = IndexService(audit_path=str(tmp_path / "audit.jsonl"))

    payload = captured["config"]
    assert isinstance(payload, dict)
    assert payload["embeddings"]["provider"] == service._llm_provider
    assert payload["embeddings"][service._llm_provider]["model"] == service._llm_model
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_backend_health_check_works_inside_running_event_loop(
    monkeypatch: pytest.MonkeyPatch, service: IndexService
) -> None:
    calls: list[str | None] = []
    loops: list[int] = []

    async def _fake_health_check(provider_id: str | None = None) -> bool:
        calls.append(provider_id)
        loops.append(id(asyncio.get_running_loop()))
        await asyncio.sleep(0)
        return True

    monkeypatch.setattr(service.vdb, "health_check", _fake_health_check)

    async def _invoke() -> tuple[dict[str, str], dict[str, str]]:
        first = service.backend_health_check(provider_id="qdrant")
        second = service.backend_health_check(provider_id="qdrant")
        return first, second

    assert asyncio.run(_invoke()) == (
        {
            "status": "ok",
            "provider": "qdrant",
            "backend": "qdrant",
        },
        {
            "status": "ok",
            "provider": "qdrant",
            "backend": "qdrant",
        },
    )
    assert calls == ["qdrant", "qdrant"]
    assert len(set(loops)) == 1
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_search_engine_filter_validation_and_execution() -> None:
    adapter = InMemoryVdbAdapter()
    adapter.create_collection("engine_cov")
    adapter.upsert("engine_cov", "doc-1", ["alpha beta"], [[0.1, 0.2]], {"tenant": "alpha"})

    assert validate_filters(None) == {}
    with pytest.raises(ValueError):
        validate_filters({1: "invalid-key"})

    engine = SearchEngine(adapter=adapter)
    rows = engine.search("engine_cov", " alpha   beta ", filters={"tenant": "alpha"})
    assert rows
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_inmemory_vdb_filter_threshold_and_empty_query_paths() -> None:
    adapter = InMemoryVdbAdapter()
    adapter.create_collection("adapter_cov")
    adapter.upsert("adapter_cov", "doc-1", ["alpha beta"], [[0.1, 0.2]], {"tenant": "alpha"})

    assert adapter.query("adapter_cov", "alpha", filters={"tenant": "beta"}) == []
    assert adapter.query("adapter_cov", "alpha", score_threshold=1.1) == []

    adapter_empty = InMemoryVdbAdapter()
    adapter_empty.create_collection("adapter_empty")
    adapter_empty.upsert("adapter_empty", "doc-empty", [""], [[0.1, 0.2]], {"tenant": "alpha"})
    assert adapter_empty.query("adapter_empty", "alpha", top_k=1) == []
