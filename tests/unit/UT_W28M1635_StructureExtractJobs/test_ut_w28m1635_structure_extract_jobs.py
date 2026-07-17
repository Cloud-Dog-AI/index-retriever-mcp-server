# ---------------------------------------------------------------------------
# Licence: Proprietary - Cloud-Dog AI platform
# Owner: index-retriever-mcp-server
# Description: W28M-1635 - queued document-structure extraction.
#   Proves a parser run that outlives the platform synchronous request ceiling
#   (cloud_dog_api_kit TimeoutMiddleware, 30s default) still completes, because the
#   extraction is queued and polled instead of blocking a request.
# Related: W28M-1635 (TB country report v7), W28M-1626 (MinerU structure ingestion)
# Tests: UT_W28M1635_StructureExtractJobs
# ---------------------------------------------------------------------------
"""Unit tests for W28M-1635 queued structure extraction.

Regression context: `structure/extract` was synchronous only. A real country-report
PDF parses in ~70s+, while `TimeoutMiddleware` bounds any request at 30s by default,
so every real extraction failed closed with
``{"code":"TIMEOUT","message":"Request timed out after 30.0s"}`` on both the API and
MCP transports. These tests pin the queued path that removes that ceiling.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from index_tools.db.runtime import initialise_database, shutdown_database

# The synchronous request ceiling this feature exists to escape
# (cloud_dog_api_kit.middleware.timeout.TimeoutMiddleware default).
SYNC_REQUEST_CEILING_SECONDS = 30.0


def _configure_sqlite_env(monkeypatch, db_path: Path) -> None:
    """Point the service at an isolated sqlite database for this test."""
    monkeypatch.setenv("CLOUD_DOG_DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG_DB__DATABASE", str(db_path))
    monkeypatch.setenv("CLOUD_DOG__DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG__DB__DATABASE", str(db_path))
    for name in (
        "CLOUD_DOG__DB__URL",
        "CLOUD_DOG_DB__URL",
        "CLOUD_DOG__INDEX__DB__URL",
        "INDEX_RETRIEVER_DB_URL",
        "DB_URL",
    ):
        monkeypatch.delenv(name, raising=False)


class _CapturingAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def log_admin_action(self, **kwargs) -> None:  # noqa: ANN003
        self.events.append(kwargs)


@pytest.fixture()
def index_service(monkeypatch, tmp_path: Path):
    """Real IndexService on an isolated sqlite queue, with embedding config satisfied."""
    _configure_sqlite_env(monkeypatch, tmp_path / "w28m1635-ut.db")
    monkeypatch.setenv("CLOUD_DOG__INDEX__EMBEDDING__PROVIDER", "hash")
    monkeypatch.setenv("EMBED_PROVIDER", "hash")
    initialise_database(force_reinit=True)
    from index_tools.tools.service import IndexService

    service = IndexService(audit_path=str(tmp_path / "audit.jsonl"))
    # Run queued work inline so the test asserts the handler contract deterministically
    # rather than racing a detached dispatch thread.
    monkeypatch.setattr(service, "_dispatch_job_detached", lambda job_id: None, raising=False)
    monkeypatch.setattr(service, "_dispatch_job_async", lambda job_id: None, raising=False)
    try:
        yield service
    finally:
        shutdown_database()


@pytest.fixture()
def unstubbed_index_service(monkeypatch, tmp_path: Path):
    """IndexService with the real dispatcher, to exercise actual thread detachment.

    `index_service` stubs dispatch so handler contracts can be asserted deterministically;
    that stubbing is exactly what hid the inline-blocking defect, so this fixture leaves
    the dispatcher real. `_async_job_execution` is forced false to reproduce the deployed
    condition where `_dispatch_job_async` would otherwise run the job inline.
    """
    _configure_sqlite_env(monkeypatch, tmp_path / "w28m1635-ut-detach.db")
    monkeypatch.setenv("CLOUD_DOG__INDEX__EMBEDDING__PROVIDER", "hash")
    monkeypatch.setenv("EMBED_PROVIDER", "hash")
    initialise_database(force_reinit=True)
    from index_tools.tools.service import IndexService

    service = IndexService(audit_path=str(tmp_path / "audit-detach.jsonl"))
    service._async_job_execution = False
    try:
        yield service
    finally:
        shutdown_database()


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-007")
def test_structure_extract_job_type_is_registered(index_service) -> None:
    """The queue must own a `structure_extract` handler, like ingest_text/reindex_run."""
    handler = index_service.queue._job_callbacks.get("structure_extract") or getattr(
        index_service.queue, "_handlers", {}
    ).get("structure_extract")
    assert handler is not None or hasattr(index_service, "_process_structure_extract_job")


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-007")
def test_extract_structure_async_returns_job_without_blocking(index_service) -> None:
    """Submitting returns a job id immediately; nothing is parsed on the caller's thread.

    This is the property that defeats the 30s ceiling: the submit does no parsing.
    """
    calls: list[dict] = []

    def _never_called(*args, **kwargs):  # noqa: ANN002, ANN003
        calls.append(kwargs)
        raise AssertionError("extract_file must not run on the submitting thread")

    job_id = index_service.extract_structure_async(
        b"# Country Report\n\nOverview.\n\n## Governance\n\nDetail.\n",
        filename="report.md",
        mime_type="text/markdown",
        profile="p",
        collection="c",
        provider="internal",
        actor="tester",
    )
    assert job_id
    assert calls == []
    job = index_service.job_get(job_id)
    assert job.job_type == "structure_extract"


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-007")
def test_queued_extraction_completes_past_the_sync_request_ceiling(index_service, monkeypatch) -> None:
    """A parse slower than the 30s sync ceiling still completes via the queue.

    Reproduces the exact production failure: the synchronous route could never finish
    this work because TimeoutMiddleware killed the request at 30.0s. The queued handler
    has no request bound, so the same parse completes and the id is recorded.
    """
    observed: dict[str, object] = {}

    def _slow_extract(data, **kwargs):  # noqa: ANN001, ANN003
        # Declares a parse duration beyond the synchronous ceiling without sleeping.
        observed["elapsed_seconds"] = SYNC_REQUEST_CEILING_SECONDS * 3
        observed["provider"] = kwargs.get("provider")
        return {"document": {"structure_document_id": "sd_w28m1635"}, "sections": [{}, {}]}

    monkeypatch.setattr(index_service.structure, "extract_file", _slow_extract, raising=False)

    job_id = index_service.extract_structure_async(
        b"%PDF-1.7 fake country report bytes",
        filename="Country Report Sweden July 2026.pdf",
        mime_type="application/pdf",
        profile="p",
        collection="c",
        provider="mineru",
        actor="tester",
    )
    index_service.queue.run(job_id)

    assert float(observed["elapsed_seconds"]) > SYNC_REQUEST_CEILING_SECONDS
    assert observed["provider"] == "mineru"
    job = index_service.job_get(job_id)
    assert str(getattr(job.status, "value", job.status)) == "succeeded"
    assert job.progress.get("structure_document_id") == "sd_w28m1635"


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-007")
def test_handler_falls_back_to_flat_structure_document_id(index_service, monkeypatch) -> None:
    """A provider reporting the id at the top level is still recorded.

    The nested `document.structure_document_id` shape is covered by the ceiling test;
    this pins the flat fallback so neither provider shape silently records an empty id.
    """
    monkeypatch.setattr(
        index_service.structure,
        "extract_file",
        lambda data, **kw: {"structure_document_id": "sd_flat", "sections": []},
        raising=False,
    )
    job_id = index_service.extract_structure_async(
        b"flat-provider-bytes",
        filename="flat.pdf",
        mime_type="application/pdf",
        profile="p",
        collection="c",
        provider="internal",
        actor="tester",
    )
    index_service.queue.run(job_id)
    assert index_service.job_get(job_id).progress.get("structure_document_id") == "sd_flat"


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-007")
def test_submit_detaches_and_never_runs_inline(unstubbed_index_service, monkeypatch) -> None:
    """The submit must return while the parse is still running, on a detached thread.

    Regression: `_dispatch_job_async` runs a job inline whenever
    `_async_job_execution` is false. Routing the submit through it blocked the caller
    for the whole parse and re-tripped the very request ceiling the queue exists to
    escape — the deployed API returned 504 even though the job later succeeded. This
    test deliberately does NOT stub the dispatcher, which is how that escaped.
    """
    service = unstubbed_index_service
    started = threading.Event()
    release = threading.Event()

    def _blocking_extract(data, **kwargs):  # noqa: ANN001, ANN003
        started.set()
        # Hold the parse open; a submit that waits for this has blocked the caller.
        assert release.wait(timeout=30), "handler was never released"
        return {"document": {"structure_document_id": "sd_detached"}, "sections": []}

    monkeypatch.setattr(service.structure, "extract_file", _blocking_extract, raising=False)

    submitted = time.monotonic()
    job_id = service.extract_structure_async(
        b"detach-me",
        filename="Country Report Kenya July 2026.pdf",
        mime_type="application/pdf",
        profile="p",
        collection="c",
        provider="mineru",
        actor="tester",
    )
    submit_seconds = time.monotonic() - submitted

    # The submit returned while the parse is still in flight.
    assert job_id
    assert submit_seconds < 5.0, f"submit blocked for {submit_seconds:.1f}s"
    assert started.wait(timeout=10), "extraction never started on a worker thread"
    release.set()

    for _ in range(100):
        if str(getattr(service.job_get(job_id).status, "value", "")) == "succeeded":
            break
        time.sleep(0.1)
    assert service.job_get(job_id).progress.get("structure_document_id") == "sd_detached"


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-007")
def test_resubmitting_same_document_is_idempotent(index_service, monkeypatch) -> None:
    """A repeated submit returns the same job id, so a resumed rescan cannot duplicate work."""
    monkeypatch.setattr(
        index_service.structure,
        "extract_file",
        lambda data, **kw: {"document": {"structure_document_id": "sd_x"}, "sections": []},
        raising=False,
    )
    payload = dict(
        filename="Country Report Jordan 2026.pdf",
        mime_type="application/pdf",
        profile="p",
        collection="c",
        provider="mineru",
        actor="tester",
    )
    first = index_service.extract_structure_async(b"same-bytes", **payload)
    second = index_service.extract_structure_async(b"same-bytes", **payload)
    assert first == second


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-007")
def test_parser_upgrade_forces_reextraction(index_service, monkeypatch) -> None:
    """Identical bytes must re-extract after a parser upgrade, not return the old job.

    Regression: the idempotency key hashed only the document bytes, so once
    cloud-dog-vdb gained MinerU table recovery, resubmitting the same PDF returned the
    previous version's table-less job and nothing re-parsed. A whole corpus rescan
    reported "succeeded" while silently yielding the old results.
    """
    monkeypatch.setattr(
        index_service.structure,
        "extract_file",
        lambda data, **kw: {"document": {"structure_document_id": "sd_v"}, "sections": []},
        raising=False,
    )
    payload = dict(
        filename="Country Report India July 2026.pdf",
        mime_type="application/pdf",
        profile="p",
        collection="c",
        provider="mineru",
        actor="tester",
    )
    monkeypatch.setattr(
        type(index_service), "_parser_version", staticmethod(lambda provider: "cloud-dog-vdb==0.5.5")
    )
    before = index_service.extract_structure_async(b"identical-bytes", **payload)

    monkeypatch.setattr(
        type(index_service), "_parser_version", staticmethod(lambda provider: "cloud-dog-vdb==0.5.7")
    )
    after = index_service.extract_structure_async(b"identical-bytes", **payload)

    assert before != after, "parser upgrade must not reuse the previous extraction"


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-007")
def test_parser_version_is_part_of_the_key(index_service) -> None:
    """The live parser version is reported, so the key can bind to it."""
    assert index_service._parser_version("internal") == "internal"
    assert index_service._parser_version("mineru").startswith("cloud-dog-vdb==")


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-007")
def test_ir_table_blocks_become_populated_structure_tables() -> None:
    """A parser's TableBlock must survive into a StructureTable with real cells.

    Regression: normalise_ir_to_bundle read `tb.markdown`/`tb.text`, which DocumentIR's
    TableBlock does not define, so every recovered table was persisted as an empty
    shell — 4 tables with 0 cells for a real report. Reading a non-existent attribute
    failed silently, which is why only live inspection surfaced it.
    """
    from cloud_dog_vdb.ingestion.parse.ir import DocumentIR, TableBlock

    from index_tools.structure.extract import normalise_ir_to_bundle

    ir = DocumentIR(
        source_uri="Country Report Morocco July 2026.pdf",
        provider_id="mineru",
        provider_version="api-0.1.0",
        table_blocks=[
            TableBlock(
                headers=["Indicator", "Value"],
                rows=[["Life expectancy", "74.3"], ["Infant mortality", "16.8"]],
                locator="table[0]",
            )
        ],
    )
    bundle = normalise_ir_to_bundle(
        ir, profile="p", collection="c", source_filename="Morocco.pdf", provider="mineru"
    )
    assert len(bundle.tables) == 1
    table = bundle.tables[0]
    assert table.row_count == 3, "header row + 2 data rows"
    assert table.column_count == 2
    assert table.header_rows == 1
    assert len(table.cells) == 6, f"2 headers + 4 data cells, got {len(table.cells)}"
    assert {"row": 0, "column": 0, "text": "Indicator", "is_header": True} in table.cells
    assert {"row": 1, "column": 1, "text": "74.3", "is_header": False} in table.cells
    assert "Life expectancy" in (table.normalised_markdown or "")
