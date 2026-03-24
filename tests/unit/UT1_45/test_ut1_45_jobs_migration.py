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

import time
from pathlib import Path

import pytest

from index_tools.queue.engine import QueueEngine
from index_tools.queue.models import JobRecord, JobStatus


def test_jobs_backend_lifecycle_with_retry(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'jobs-retry.db'}"
    engine = QueueEngine(
        database_url=database_url,
        server_id="ut-jobs-retry",
        timeout_seconds=5,
        retry_max_attempts=2,
        retry_backoff_seconds=0.01,
    )
    attempts = {"count": 0}

    def flaky(job: JobRecord) -> None:
        assert job.server_id in {"ut-jobs-retry", "index-retriever-local"}
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient failure")

    engine.register_handler("ingest_text", flaky)
    queued = engine.enqueue(
        JobRecord(
            job_id="job-retry",
            profile="default",
            collection="jobs",
            job_type="ingest_text",
            idempotency_key="retry-key",
        ),
        payload={"profile": "default", "collection": "jobs", "text": "payload", "source": "inline://retry"},
        actor="unit",
    )

    result = engine.run(queued.job_id)
    assert result.status is JobStatus.succeeded
    assert attempts["count"] == 2

    status = engine.queue_status()
    assert status["backend"] == "cloud_dog_jobs"
    assert status["server_id"] == "ut-jobs-retry"
    assert status["failed"] == 0


def test_jobs_backend_timeout_marks_terminal_status(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'jobs-timeout.db'}"
    engine = QueueEngine(
        database_url=database_url,
        server_id="ut-jobs-timeout",
        timeout_seconds=1,
        retry_max_attempts=1,
        retry_backoff_seconds=0.01,
    )

    def slow(_: JobRecord) -> None:
        time.sleep(1.2)

    engine.register_handler("ingest_text", slow)
    queued = engine.enqueue(
        JobRecord(
            job_id="job-timeout",
            profile="default",
            collection="jobs",
            job_type="ingest_text",
        ),
        payload={"profile": "default", "collection": "jobs", "text": "payload", "source": "inline://timeout"},
    )

    with pytest.raises(TimeoutError, match="timed out"):
        engine.run(queued.job_id)

    assert engine.get(queued.job_id).status is JobStatus.timeout
