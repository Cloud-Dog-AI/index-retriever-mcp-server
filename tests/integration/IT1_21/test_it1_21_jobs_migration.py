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

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from index_tools.queue.engine import QueueEngine
from index_tools.queue.models import JobRecord, JobStatus


def test_jobs_backend_concurrency_and_recovery(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'it1_21_jobs.db'}"
    processed: list[str] = []
    lock = threading.Lock()

    def _handler(job: JobRecord) -> None:
        time.sleep(0.05)
        with lock:
            processed.append(job.job_id)

    engine_a = QueueEngine(database_url=database_url, server_id="it1-21-a", retry_backoff_seconds=0.01)
    engine_b = QueueEngine(database_url=database_url, server_id="it1-21-b", retry_backoff_seconds=0.01)
    engine_recovery = QueueEngine(database_url=database_url, server_id="it1-21-recovery", retry_backoff_seconds=0.01)
    for engine in (engine_a, engine_b, engine_recovery):
        engine.register_handler("ingest_text", _handler)

    queued_jobs = [
        engine_a.enqueue(
            JobRecord(
                job_id=f"job-{idx}",
                profile="default",
                collection="jobs",
                job_type="ingest_text",
                idempotency_key=f"job-{idx}",
            ),
            payload={
                "profile": "default",
                "collection": "jobs",
                "text": f"payload-{idx}",
                "source": f"inline://job-{idx}",
            },
            actor="integration",
        )
        for idx in range(4)
    ]

    def _drain(engine: QueueEngine) -> int:
        count = 0
        while True:
            processed_now = engine.process_available(limit=1)
            if processed_now == 0:
                return count
            count += processed_now

    with ThreadPoolExecutor(max_workers=2) as executor:
        counts = [future.result() for future in [executor.submit(_drain, engine_a), executor.submit(_drain, engine_b)]]

    assert sum(counts) == 4
    assert sorted(processed) == [f"job-{idx}" for idx in range(4)]
    assert {engine_a.get(job.job_id).status for job in queued_jobs} == {JobStatus.succeeded}

    recovery_job = engine_a.enqueue(
        JobRecord(
            job_id="job-recovery",
            profile="default",
            collection="jobs",
            job_type="ingest_text",
            idempotency_key="job-recovery",
        ),
        payload={
            "profile": "default",
            "collection": "jobs",
            "text": "payload-recovery",
            "source": "inline://job-recovery",
        },
        actor="integration",
    )

    recovered = engine_recovery.run(recovery_job.job_id)
    assert recovered.status is JobStatus.succeeded
    assert engine_recovery.get(recovery_job.job_id).server_id == "it1-21-recovery"
