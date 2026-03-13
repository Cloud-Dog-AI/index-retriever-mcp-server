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

# index-retriever-mcp-server — Queue Engine
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Queue execution helper via cloud_dog_jobs integration.

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256

from index_tools.queue.models import JobRecord, JobStatus

try:
    import cloud_dog_jobs  # type: ignore
except ImportError:  # pragma: no cover
    cloud_dog_jobs = None


class QueueEngine:
    """In-process queue fallback used for deterministic unit tests."""

    def __init__(self) -> None:
        """Initialise the instance state."""
        self._jobs: dict[str, JobRecord] = {}

    def generate_idempotency_key(self, profile: str, collection: str, source: str) -> str:
        """Execute generate idempotency key."""
        digest = sha256(f"{profile}|{collection}|{source}".encode()).hexdigest()
        return digest

    def enqueue(self, job: JobRecord) -> None:
        """Execute enqueue."""
        self._jobs[job.job_id] = job

    def get(self, job_id: str) -> JobRecord:
        """Execute get."""
        return self._jobs[job_id]

    def list_jobs(self) -> list[JobRecord]:
        """Execute list jobs."""
        return [self._jobs[job_id] for job_id in sorted(self._jobs.keys())]

    def run(self, job_id: str, handler: Callable[[JobRecord], None]) -> JobRecord:
        """Execute run."""
        job = self._jobs[job_id]
        job.status = JobStatus.running
        try:
            handler(job)
            job.status = JobStatus.succeeded
        except Exception:
            job.status = JobStatus.failed
            raise
        return job

    def backend_name(self) -> str:
        """Execute backend name."""
        if cloud_dog_jobs is not None:
            return "cloud_dog_jobs"
        return "fallback"
