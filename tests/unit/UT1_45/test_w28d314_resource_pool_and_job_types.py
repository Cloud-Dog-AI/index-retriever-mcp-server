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

"""W28D-314: Verify resource pool fields, retention_run and reindex_run job types."""

from __future__ import annotations

from pathlib import Path

import pytest

from index_tools.queue.engine import QueueEngine
from index_tools.queue.models import JobRecord, JobStatus


def _make_engine(tmp_path: Path) -> QueueEngine:
    return QueueEngine(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'w28d314.db'}",
        server_id="ut-w28d314",
        timeout_seconds=10,
        retry_max_attempts=1,
        retry_backoff_seconds=0.01,
    )


def test_enqueue_passes_resources_to_job_constructor(tmp_path: Path) -> None:
    """Verify that resources dict flows through enqueue to the Job constructor."""
    engine = _make_engine(tmp_path)
    captured = {}

    original_enqueue = engine._backend.enqueue

    def spy_enqueue(job):
        captured["resources"] = dict(job.resources) if job.resources else {}
        return original_enqueue(job)

    engine._backend.enqueue = spy_enqueue
    engine.register_handler("ingest_text", lambda job: None)

    queued = engine.enqueue(
        JobRecord(
            job_id="res-test-1",
            profile="default",
            collection="test",
            job_type="ingest_text",
        ),
        payload={"profile": "default", "collection": "test", "text": "hello", "source": "inline://test"},
        actor="unit",
        resources={"embedding-pool": 1},
    )
    assert queued.status is JobStatus.queued
    assert captured["resources"] == {"embedding-pool": 1}


def test_enqueue_without_resources_defaults_empty(tmp_path: Path) -> None:
    """Verify that omitting resources gives empty dict."""
    engine = _make_engine(tmp_path)
    captured = {}

    original_enqueue = engine._backend.enqueue

    def spy_enqueue(job):
        captured["resources"] = dict(job.resources) if job.resources else {}
        return original_enqueue(job)

    engine._backend.enqueue = spy_enqueue
    engine.register_handler("ingest_text", lambda job: None)

    queued = engine.enqueue(
        JobRecord(
            job_id="res-test-2",
            profile="default",
            collection="test",
            job_type="ingest_text",
        ),
        payload={"profile": "default", "collection": "test", "text": "hello", "source": "inline://test"},
        actor="unit",
    )
    assert queued.status is JobStatus.queued
    assert captured["resources"] == {}


def test_retention_run_handler_registered_and_executes(tmp_path: Path) -> None:
    """Verify retention_run job type can be registered and executed."""
    engine = _make_engine(tmp_path)
    calls = {"count": 0}

    def retention_handler(job: JobRecord) -> None:
        assert job.job_type == "retention_run"
        payload = dict(job.payload)
        assert payload["profile"] == "default"
        assert payload["collection"] == "test"
        assert int(payload["older_than_days"]) == 30
        calls["count"] += 1

    engine.register_handler("retention_run", retention_handler)

    queued = engine.enqueue(
        JobRecord(
            job_id="retention-1",
            profile="default",
            collection="test",
            job_type="retention_run",
        ),
        payload={"profile": "default", "collection": "test", "older_than_days": 30, "actor": "unit"},
        actor="unit",
    )
    result = engine.run(queued.job_id)
    assert result.status is JobStatus.succeeded
    assert calls["count"] == 1


def test_reindex_run_handler_registered_and_executes(tmp_path: Path) -> None:
    """Verify reindex_run job type can be registered and executed."""
    engine = _make_engine(tmp_path)
    calls = {"count": 0}

    def reindex_handler(job: JobRecord) -> None:
        assert job.job_type == "reindex_run"
        payload = dict(job.payload)
        assert payload["profile"] == "default"
        assert payload["collection"] == "test"
        calls["count"] += 1

    engine.register_handler("reindex_run", reindex_handler)

    captured = {}
    original_enqueue = engine._backend.enqueue

    def spy_enqueue(job):
        captured["resources"] = dict(job.resources) if job.resources else {}
        return original_enqueue(job)

    engine._backend.enqueue = spy_enqueue

    queued = engine.enqueue(
        JobRecord(
            job_id="reindex-1",
            profile="default",
            collection="test",
            job_type="reindex_run",
        ),
        payload={"profile": "default", "collection": "test", "actor": "unit"},
        actor="unit",
        resources={"embedding-pool": 1},
    )
    assert captured["resources"] == {"embedding-pool": 1}

    result = engine.run(queued.job_id)
    assert result.status is JobStatus.succeeded
    assert calls["count"] == 1


def test_package_version_pins() -> None:
    """Verify cloud_dog_jobs 0.4.0 features are available."""
    from cloud_dog_jobs.domain.models import Job
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(Job)}
    assert "resources" in field_names, "Job.resources field required for PS-95 resource pools"
    assert "depends_on" in field_names, "Job.depends_on field required for PS-95 dependency edges"
