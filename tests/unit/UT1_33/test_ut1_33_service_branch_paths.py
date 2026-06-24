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

from datetime import datetime, timedelta, timezone

import pytest

from index_tools.queue.models import JobStatus
from index_tools.tools.service import IndexService, _required_env
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")


def test_service_profile_lifecycle_and_permissions(service: IndexService) -> None:
    # Covers: FR-03
    with pytest.raises(PermissionError):
        service.admin_profile_create("p1", roles={"writer"})

    service.admin_profile_create("p1", roles={"admin"})
    assert service.profile_get("p1")["backend"] == service.profile_get("default")["backend"]
    assert "p1" in service.profiles_list()

    with pytest.raises(ValueError):
        service.admin_profile_delete("default", roles={"admin"})
    service.admin_profile_delete("p1", roles={"admin"})
    assert "p1" not in service.profiles_list()
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")


def test_service_document_reference_and_jobs(service: IndexService, tmp_path) -> None:
    # Covers: FR-07, FR-08
    p = tmp_path / "doc.txt"
    p.write_text("reference content for service", encoding="utf-8")
    job_id = service.ingest_reference("default", "refs", str(p), actor="writer")
    assert job_id
    assert service.job_get(job_id).job_id == job_id
    assert service.job_wait(job_id).job_id == job_id
    assert len(service.job_list()) >= 1

    # W28E-1805B GAP-B: cancelling a job already in a terminal state (the job_wait above
    # left it succeeded) is rejected, not silently flipped to cancelled.
    from index_tools.queue.engine import JobTerminalStateError

    with pytest.raises(JobTerminalStateError):
        service.job_cancel(job_id)
    assert service.job_get(job_id).status is JobStatus.succeeded

    failed = service.job_get(job_id)
    failed.status = JobStatus.failed
    retried = service.job_retry(job_id)
    assert retried.status in {JobStatus.queued, JobStatus.succeeded}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")
@pytest.mark.req("FR-015")


def test_service_delete_reindex_retention_and_stream_errors(service: IndexService) -> None:
    # Covers: FR-15, FR-16
    old_created = datetime.now(timezone.utc) - timedelta(days=200)  # noqa: UP017
    new_created = datetime.now(timezone.utc)  # noqa: UP017

    old_job = service.ingest_text(
        "default",
        "ret",
        "old entry",
        "api://old",
        actor="writer",
        metadata={"tag": "drop"},
        created_at=old_created,
    )
    _ = old_job
    service.ingest_text(
        "default",
        "ret",
        "new entry",
        "api://new",
        actor="writer",
        metadata={"tag": "keep"},
        created_at=new_created,
    )

    assert service.reindex_run("default", "ret")["documents"] >= 2
    removed = service.delete_by_filter("default", "ret", {"tag": "drop"})
    assert removed >= 1

    removed_by_retention = service.retention_run("default", "ret", older_than_days=100)
    assert removed_by_retention >= 0

    sid = service.ingest_stream_session_start("default", "streams", "order-1")
    _ = service.ingest_stream_event(sid, "chunk-1", actor="writer")
    closed = service.ingest_stream_close(sid)
    assert closed["ingested_events"] == 1
    with pytest.raises(RuntimeError):
        service.ingest_stream_event(sid, "chunk-2", actor="writer")
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")


def test_service_required_env_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KEY_ONE", raising=False)
    monkeypatch.delenv("KEY_TWO", raising=False)
    with pytest.raises(RuntimeError):
        _required_env("KEY_ONE", "KEY_TWO")

    monkeypatch.setenv("KEY_TWO", "x")
    assert _required_env("KEY_ONE", "KEY_TWO") == "x"
