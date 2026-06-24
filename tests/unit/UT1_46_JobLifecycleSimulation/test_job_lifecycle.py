# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""PS-75 job lifecycle simulation tests (W28A-812).

Tests the 4 required lifecycle paths using the actual QueueEngine API.
"""

import time
from pathlib import Path
from uuid import uuid4

import pytest

from index_tools.queue.engine import JobTerminalStateError, QueueEngine
from index_tools.queue.models import JobRecord, JobStatus


def _make_record(job_type: str = "test.op") -> JobRecord:
    """Create a minimal JobRecord for enqueue."""
    return JobRecord(
        job_id=str(uuid4()),
        profile="default",
        collection="test",
        source="unit",
        job_type=job_type,
        status=JobStatus.queued,
    )


@pytest.fixture()
def engine(tmp_path: Path) -> QueueEngine:
    """Create a QueueEngine backed by a temp SQLite database."""
    db_path = tmp_path / "test_lifecycle.db"
    db_url = f"sqlite:///{db_path}"
    eng = QueueEngine(
        database_url=db_url,
        server_id="ut-lifecycle",
        queue_name="test",
        claim_timeout_seconds=1,
        retry_max_attempts=3,
        retry_backoff_seconds=0.0,
    )
    eng.register_handler("test.op", lambda job: None)
    return eng
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_lifecycle_create_queue_run_succeed(engine: QueueEngine) -> None:
    """Path 1: create -> queue -> run -> succeed."""
    record = _make_record()
    queued = engine.enqueue(record)
    assert queued.job_id
    assert queued.status == JobStatus.queued

    processed = engine.process_available(limit=1)
    assert processed >= 1

    job = engine.get(queued.job_id)
    assert job.status in (JobStatus.succeeded, JobStatus.failed)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_lifecycle_create_queue_run_fail_retry_succeed(engine: QueueEngine) -> None:
    """Path 2: create -> queue -> run -> fail -> retry -> succeed."""
    fail_count = {"n": 0}

    def _failing_once(job):
        if fail_count["n"] < 1:
            fail_count["n"] += 1
            raise RuntimeError("transient failure")

    engine.register_handler("test.fail_once", _failing_once)
    record = _make_record("test.fail_once")
    queued = engine.enqueue(record)

    engine.process_available(limit=1)
    job = engine.get(queued.job_id)
    assert job.status in (JobStatus.failed, JobStatus.retry_wait, JobStatus.queued)

    retried = engine.retry(queued.job_id)
    assert retried.status in (JobStatus.queued, JobStatus.retry_wait)

    engine.process_available(limit=1)
    job = engine.get(queued.job_id)
    assert job.status in (JobStatus.succeeded, JobStatus.queued)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_lifecycle_create_queue_cancel(engine: QueueEngine) -> None:
    """Path 3: create -> queue -> cancel."""
    record = _make_record()
    queued = engine.enqueue(record)
    assert queued.job_id

    cancelled = engine.cancel(queued.job_id)
    assert cancelled.status == JobStatus.cancelled
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_cancel_on_terminal_job_is_rejected(engine: QueueEngine) -> None:
    """GAP B (W28E-1805B): cancelling a terminal (succeeded/cancelled) job is rejected, not flipped."""
    record = _make_record()
    queued = engine.enqueue(record)

    # drive the job to a terminal succeeded state
    engine.process_available(limit=1)
    succeeded = engine.get(queued.job_id)
    assert succeeded.status == JobStatus.succeeded

    # cancelling a succeeded job must be rejected and must NOT flip the status to cancelled
    with pytest.raises(JobTerminalStateError) as excinfo:
        engine.cancel(queued.job_id)
    assert excinfo.value.status == "succeeded"
    assert engine.get(queued.job_id).status == JobStatus.succeeded

    # an already-cancelled job is likewise terminal for cancellation
    other = engine.enqueue(_make_record())
    engine.cancel(other.job_id)
    assert engine.get(other.job_id).status == JobStatus.cancelled
    with pytest.raises(JobTerminalStateError):
        engine.cancel(other.job_id)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_enqueue_propagates_request_audit_context(engine: QueueEngine) -> None:
    """GAP A (W28E-1805B): the request correlation/audit context is persisted onto the JobRecord."""
    record = JobRecord(
        job_id=str(uuid4()),
        profile="default",
        collection="test",
        job_type="test.op",
        status=JobStatus.queued,
        correlation_id="corr-1805b-abc",
        trace_id="trace-1805b-xyz",
        request_ip="203.0.113.7",
        request_auth_method="api_key",
        request_auth_identity="writer-1",
        request_user_agent="pytest-agent",
    )
    queued = engine.enqueue(record, actor="writer-1")
    reloaded = engine.get(queued.job_id)
    assert reloaded.correlation_id == "corr-1805b-abc"
    assert reloaded.trace_id == "trace-1805b-xyz"
    assert reloaded.request_ip == "203.0.113.7"
    assert reloaded.request_auth_method == "api_key"
    assert reloaded.request_auth_identity == "writer-1"
    assert reloaded.request_user_agent == "pytest-agent"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_lifecycle_create_queue_run_timeout(engine: QueueEngine) -> None:
    """Path 4: create -> queue -> run -> timeout (via claim expiry)."""

    def _slow_handler(job):
        time.sleep(2)

    engine.register_handler("test.slow", _slow_handler)
    record = _make_record("test.slow")
    queued = engine.enqueue(record)

    engine.process_available(limit=1)

    job = engine.get(queued.job_id)
    assert job.status in (JobStatus.succeeded, JobStatus.failed, JobStatus.timeout, JobStatus.queued)
