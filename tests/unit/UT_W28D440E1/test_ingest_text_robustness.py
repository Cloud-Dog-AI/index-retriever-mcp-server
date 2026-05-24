# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""W28D-440E1: ingest_text large-payload robustness, structured embedding
failure details, compact source-hunt regression, and source_uri filter tests.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from index_tools.pipeline.chunking import token_chunks
from index_tools.queue.models import JobStatus
from index_tools.tools.service import EmbeddingBatchError, IndexService


def _large_markdown(word_count: int = 2400) -> str:
    """Generate a synthetic Markdown payload that produces >=50 chunks."""
    lines = []
    for i in range(word_count // 20):
        lines.append(
            f"## Section {i}\n\n"
            f"The transparent borders initiative examines cross-border data flows "
            f"between participating nations. Region {i} shows significant growth "
            f"in trade indicators and policy harmonisation metrics for the current "
            f"reporting period {2020 + i % 6}.\n"
        )
    return "\n".join(lines)


def _compact_markdown() -> str:
    """~1,300 character compact DEMO-027 source-hunt extract."""
    return (
        "# Transparent Borders DEMO-027 Compact Source Hunt Extract\n\n"
        "## Selected Sources\n\n"
        "- WHO Global Health Observatory OData API\n"
        "- UN Statistics Division SDG API\n"
        "- Eurostat Dissemination Statistics API\n"
        "- World Bank Indicators API\n"
        "- IMF DataMapper API\n\n"
        "## Summary\n\n"
        "Ten source families were evaluated for cross-border transparency "
        "indicators. The top five sources provide real-time economic, health, "
        "and demographic data suitable for the Transparent Borders reporting "
        "framework.\n"
    )


@pytest.fixture()
def service(tmp_path: Path) -> IndexService:
    audit_path = tmp_path / "audit.jsonl"
    svc = IndexService(audit_path=str(audit_path))
    try:
        yield svc
    finally:
        svc.close()


class TestIngestTextLargePayload:
    """Requirement: test_ingest_text_large_markdown_payload_succeeds_or_preflight_rejects"""

    def test_large_payload_chunks_into_at_least_50(self):
        text = _large_markdown()
        chunks = token_chunks(text, chunk_size=64, chunk_overlap=8)
        assert len(chunks) >= 50, f"Expected >=50 chunks, got {len(chunks)}"
        assert len(text) >= 16000, f"Expected >=16000 chars, got {len(text)}"

    def test_large_payload_ingest_succeeds(self, service: IndexService):
        """Large Markdown payload (>=50 chunks) should succeed through batched upsert."""
        text = _large_markdown()
        chunks = token_chunks(text, chunk_size=64, chunk_overlap=8)
        assert len(chunks) >= 50

        job_id = service.ingest_text(
            profile="default",
            collection="test-large",
            text=text,
            source="file-mcp:test/large-source-hunt-repro.md",
            actor="test",
        )
        assert job_id
        job = service.queue.get(job_id)
        assert job.status == JobStatus.succeeded, (
            f"Expected succeeded, got {job.status}. "
            f"last_error={job.last_error}"
        )

    def test_large_payload_produces_chunk_records(self, service: IndexService):
        """Verify that batched upsert creates per-chunk records with chunk_index metadata."""
        text = _large_markdown()
        job_id = service.ingest_text(
            profile="default",
            collection="test-chunks",
            text=text,
            source="file-mcp:test/chunk-records.md",
            actor="test",
        )
        job = service.queue.get(job_id)
        assert job.status == JobStatus.succeeded

        # Search to verify records exist
        results = service.search(
            profile="default",
            collection="test-chunks",
            query="transparent borders trade indicators",
            top_k=5,
        )
        assert len(results) > 0, "Search should return results from ingested chunks"


class TestEmbeddingBackend500:
    """Requirement: test_embedding_backend_500_records_chunk_context"""

    def test_embedding_batch_error_has_structured_details(self):
        err = EmbeddingBatchError(
            batch_start=12,
            batch_size=10,
            chunk_count=37,
            embedding_model="nomic-embed-text",
            provider="ollama",
            provider_error="Ollama embedding failed: 500",
            profile="demo27-transparent-borders",
            collection="report-generation",
        )
        details = err.to_error_details()
        assert details["chunk_count"] == 37
        assert details["failed_chunk_index"] == 12
        assert details["embedding_model"] == "nomic-embed-text"
        assert details["provider"] == "ollama"
        assert details["provider_http_status"] == 500
        assert details["retryable"] is True
        assert details["suggested_action"] == "retry_later_or_ingest_compact_extract"
        assert details["profile"] == "demo27-transparent-borders"
        assert details["collection"] == "report-generation"

    def test_embedding_failure_surfaces_in_job_error(self, service: IndexService):
        """When the VDB adapter raises during upsert, the job's last_error
        must include structured details from EmbeddingBatchError."""
        text = _large_markdown(word_count=200)

        # Patch upsert_records to simulate Ollama 500
        original_upsert = service.vdb.upsert_records

        call_count = {"n": 0}

        async def _failing_upsert(collection, records, **kwargs):
            call_count["n"] += 1
            raise RuntimeError("Ollama embedding failed: 500")

        service.vdb.upsert_records = _failing_upsert  # type: ignore[assignment]
        try:
            job_id = service.ingest_text(
                profile="default",
                collection="test-fail",
                text=text,
                source="file-mcp:test/fail-embed.md",
                actor="test",
            )
            job = service.queue.get(job_id)
            assert job.status in (JobStatus.dead_lettered, JobStatus.failed), (
                f"Expected dead_lettered/failed, got {job.status}"
            )
            assert job.last_error is not None
            assert "details" in job.last_error, (
                f"last_error should contain structured 'details': {job.last_error}"
            )
            details = job.last_error["details"]
            assert "chunk_count" in details
            assert "failed_chunk_index" in details
            assert "embedding_model" in details
            assert "provider" in details
            assert "retryable" in details
            assert "suggested_action" in details
        finally:
            service.vdb.upsert_records = original_upsert  # type: ignore[assignment]


class TestCompactSourceHuntRegression:
    """Requirement: test_compact_source_hunt_extract_regression"""

    def test_compact_extract_succeeds(self, service: IndexService):
        """Compact DEMO-027 source-hunt extract (~1,300 chars) must succeed."""
        text = _compact_markdown()
        assert len(text) < 2000

        job_id = service.ingest_text(
            profile="default",
            collection="test-compact",
            text=text,
            source="file-mcp:demo27-transparent-borders-report-generation/captures/compact-index-extract.md",
            actor="test",
        )
        job = service.queue.get(job_id)
        assert job.status == JobStatus.succeeded, (
            f"Compact extract should succeed, got {job.status}. "
            f"last_error={job.last_error}"
        )

    def test_compact_extract_searchable(self, service: IndexService):
        """Search must find the compact extract by content."""
        text = _compact_markdown()
        source_uri = "file-mcp:demo27-transparent-borders-report-generation/captures/compact-index-extract.md"

        service.ingest_text(
            profile="default",
            collection="test-compact-search",
            text=text,
            source=source_uri,
            actor="test",
        )
        results = service.search(
            profile="default",
            collection="test-compact-search",
            query="WHO Global Health Observatory transparent borders",
            top_k=5,
        )
        assert len(results) > 0, "Compact extract must be searchable"
        found_source = any(
            source_uri in str(r.get("source_uri", "") or r.get("source", ""))
            for r in results
        )
        assert found_source, (
            f"Expected source_uri containing compact-index-extract.md in results: "
            f"{[r.get('source_uri', r.get('source', '')) for r in results]}"
        )


class TestSearchSourceUriFilter:
    """Requirement: test_search_can_filter_current_source_uri"""

    def test_source_uri_exact_filter(self, service: IndexService):
        """Search with source_uri filter must return only matching documents."""
        old_source = "file-mcp:demo27/old-closure-extract.md"
        new_source = "file-mcp:demo27/compact-index-extract.md"

        service.ingest_text(
            profile="default",
            collection="test-filter",
            text="Old closure data about transparent borders trade metrics from 2024.",
            source=old_source,
            actor="test",
        )
        service.ingest_text(
            profile="default",
            collection="test-filter",
            text="New compact data about transparent borders trade metrics from 2026.",
            source=new_source,
            actor="test",
        )

        # Filter for new source only
        results = service.search(
            profile="default",
            collection="test-filter",
            query="transparent borders trade",
            top_k=10,
            filters={"source_uri": new_source},
        )
        assert len(results) > 0, "Filtered search must return results"
        for r in results:
            actual_uri = str(r.get("source_uri", "") or r.get("source", ""))
            assert new_source in actual_uri, (
                f"Filtered result should match source_uri={new_source}, got {actual_uri}"
            )

    def test_source_uri_filter_excludes_non_matching(self, service: IndexService):
        """source_uri filter must not return documents from other sources."""
        service.ingest_text(
            profile="default",
            collection="test-exclude",
            text="Data about transparent borders from report A.",
            source="file-mcp:demo27/report-a.md",
            actor="test",
        )
        service.ingest_text(
            profile="default",
            collection="test-exclude",
            text="Data about transparent borders from report B.",
            source="file-mcp:demo27/report-b.md",
            actor="test",
        )

        results = service.search(
            profile="default",
            collection="test-exclude",
            query="transparent borders",
            top_k=10,
            filters={"source_uri": "file-mcp:demo27/report-a.md"},
        )
        for r in results:
            actual_uri = str(r.get("source_uri", "") or r.get("source", ""))
            assert "report-b.md" not in actual_uri, (
                f"Filter for report-a should exclude report-b, got {actual_uri}"
            )
