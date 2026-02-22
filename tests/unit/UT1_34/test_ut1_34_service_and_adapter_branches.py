# index-retriever-mcp-server — UT1.34
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Branch coverage for service/search/adapter paths after live ST migration.

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from index_tools.search.engine import SearchEngine, validate_filters
from index_tools.tools.service import IndexService
from index_tools.vdb.adapters import InMemoryVdbAdapter


def test_service_collection_and_admin_paths(service: IndexService) -> None:
    service.admin_collection_create("default", "keep", roles={"admin"})
    service.collection_manager.create("other:skip")
    assert service.collections_list("default") == ["keep"]

    with pytest.raises(PermissionError):
        service.admin_collection_delete("default", "keep", roles={"writer"})
    service.admin_collection_delete("default", "keep", roles={"admin"})
    assert service.collections_list("default") == []


def test_service_idempotency_retrieve_delete_and_retention(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
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


def test_service_search_wrapper_path(service: IndexService) -> None:
    service.ingest_text("default", "search_cov", "alpha beta gamma", "api://search", actor="writer")
    rows = service.search("default", "search_cov", "alpha", top_k=5, filters=None)
    assert rows


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
