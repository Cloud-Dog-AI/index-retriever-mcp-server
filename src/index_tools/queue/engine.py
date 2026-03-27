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
from collections.abc import Callable
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from index_tools.queue.models import JobRecord, JobStatus
from sqlalchemy import MetaData, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.schema import CreateTable

try:
    import cloud_dog_jobs  # type: ignore
    from cloud_dog_jobs import JobQueue, SQLQueueBackend  # type: ignore
    from cloud_dog_jobs.backends.redis_backend import RedisQueueBackend  # type: ignore
    from cloud_dog_jobs.domain.enums import JobStatus as PlatformJobStatus  # type: ignore
    from cloud_dog_jobs.domain.models import Job  # type: ignore
    from cloud_dog_jobs.storage.sqlalchemy.models import (  # type: ignore
        build_job_call_logs_table,
        build_job_callbacks_table,
        build_job_deliveries_table,
        build_jobs_table,
    )
except ImportError:  # pragma: no cover
    cloud_dog_jobs = None
    JobQueue = None  # type: ignore[assignment]
    SQLQueueBackend = None  # type: ignore[assignment]
    RedisQueueBackend = None  # type: ignore[assignment]
    PlatformJobStatus = None  # type: ignore[assignment]
    Job = None  # type: ignore[assignment]
    build_jobs_table = None  # type: ignore[assignment]
    build_job_call_logs_table = None  # type: ignore[assignment]
    build_job_deliveries_table = None  # type: ignore[assignment]
    build_job_callbacks_table = None  # type: ignore[assignment]


def _is_sqlite_database_url(database_url: str) -> bool:
    """Return whether the normalised queue database URL targets SQLite."""
    return database_url.startswith("sqlite://")


def _queue_schema_builders() -> tuple[Callable[[MetaData], Any], ...]:
    """Return queue table builders available from cloud_dog_jobs."""
    builders = (
        build_jobs_table,
        build_job_call_logs_table,
        build_job_deliveries_table,
        build_job_callbacks_table,
    )
    return tuple(builder for builder in builders if callable(builder))


def _ensure_sqlite_queue_schema(database_url: str) -> None:
    """Create queue tables with IF NOT EXISTS semantics for SQLite startup safety."""
    if not database_url or not _is_sqlite_database_url(database_url):
        return
    builders = _queue_schema_builders()
    if not builders:
        return

    engine = create_engine(database_url, future=True)
    try:
        metadata = MetaData()
        tables = [builder(metadata) for builder in builders]
        with engine.begin() as conn:
            for table in tables:
                conn.execute(CreateTable(table, if_not_exists=True))
    finally:
        engine.dispose()


def _is_existing_table_error(exc: OperationalError) -> bool:
    """Return whether an OperationalError matches the SQLite existing-table failure."""
    message = str(exc).lower()
    return "already exists" in message and "table" in message


class QueueEngine:
    """Queue facade backed by cloud_dog_jobs."""
    # Covers: FR-07

    def __init__(
        self,
        *,
        database_url: str | None = None,
        server_id: str | None = None,
        queue_name: str | None = None,
        timeout_seconds: int | None = None,
        retry_max_attempts: int | None = None,
        retry_backoff_seconds: float | None = None,
        redis_enabled: bool | None = None,
        redis_url: str | None = None,
        redis_key_prefix: str | None = None,
    ) -> None:
        """Initialise the instance state."""
        if (
            cloud_dog_jobs is None
            or JobQueue is None
            or SQLQueueBackend is None
            or RedisQueueBackend is None
            or PlatformJobStatus is None
            or Job is None
        ):
            raise RuntimeError("cloud_dog_jobs is required for index-retriever jobs")
        self._handlers: dict[str, Callable[[JobRecord], None]] = {}
        self._job_callbacks: dict[str, Callable[[JobRecord], None]] = {}
        self._attempts: dict[str, int] = {}
        self._last_errors: dict[str, str] = {}
        self._queue_name = (queue_name or "index-retriever").strip()
        self.server_id = (server_id or "index-retriever-local").strip() or "index-retriever-local"
        self._worker_id = f"{self.server_id}-worker"
        self._timeout_seconds = 1800 if timeout_seconds is None else int(timeout_seconds)
        self._retry_max_attempts = 3 if retry_max_attempts is None else int(retry_max_attempts)
        self._retry_backoff_seconds = 5.0 if retry_backoff_seconds is None else float(retry_backoff_seconds)
        self._database_url = self._normalise_database_url(database_url)
        redis_flag = bool(redis_enabled)
        resolved_redis_url = redis_url or ""
        self._backend = None
        self._job_queue = None
        if redis_flag and resolved_redis_url:
            key_prefix = redis_key_prefix or f"index-retriever:{self.server_id}"
            self._backend = RedisQueueBackend(resolved_redis_url, key_prefix=key_prefix)
        elif self._database_url:
            _ensure_sqlite_queue_schema(self._database_url)
            try:
                self._backend = SQLQueueBackend(self._database_url)
            except OperationalError as exc:
                if not _is_existing_table_error(exc):
                    raise
                _ensure_sqlite_queue_schema(self._database_url)
                self._backend = SQLQueueBackend(self._database_url)
        else:
            raise ValueError("QueueEngine requires either queue database_url or enabled redis_url")
        self._job_queue = JobQueue(self._backend)

    @staticmethod
    def _normalise_database_url(database_url: str | None) -> str:
        raw = (database_url or "").strip()
        if not raw:
            return ""
        if raw.startswith("sqlite+aiosqlite://"):
            return "sqlite://" + raw[len("sqlite+aiosqlite://") :]
        if raw.startswith("postgresql+asyncpg://"):
            return "postgresql+psycopg://" + raw[len("postgresql+asyncpg://") :]
        return raw

    def generate_idempotency_key(self, profile: str, collection: str, source: str) -> str:
        """Execute generate idempotency key."""
        digest = sha256(f"{profile}|{collection}|{source}".encode()).hexdigest()
        return digest

    def register_handler(self, job_type: str, handler: Callable[[JobRecord], None]) -> None:
        """Register a job handler for the queue backend."""
        self._handlers[job_type] = handler

    def enqueue(
        self,
        job: JobRecord,
        *,
        payload: dict[str, Any] | None = None,
        actor: str | None = None,
        priority: int = 0,
    ) -> JobRecord:
        """Persist a queued job."""
        payload_data = dict(payload or job.payload)
        payload_data.setdefault("profile", job.profile)
        payload_data.setdefault("collection", job.collection)
        if job.ordering_key:
            payload_data.setdefault("ordering_key", job.ordering_key)
        queued_job = Job(
            job_id=job.job_id,
            job_type=job.job_type,
            queue_name=self._queue_name,
            payload=payload_data,
            status=PlatformJobStatus.QUEUED,
            priority=int(priority),
            created_at=job.created_at,
            updated_at=job.created_at,
            tenant_id=job.profile,
            host_id=self.server_id,
            idempotency_key=job.idempotency_key,
            user_id=actor,
        )
        self._backend.enqueue(queued_job)
        return self.get(job.job_id)

    def _adapt_status(self, value: Any) -> JobStatus:
        raw = str(getattr(value, "value", value)).strip().lower()
        for candidate in JobStatus:
            if candidate.value == raw:
                return candidate
        return JobStatus.failed

    def _adapt_job(self, job: Any) -> JobRecord:
        payload = dict(getattr(job, "payload", {}) or {})
        return JobRecord(
            job_id=str(job.job_id),
            profile=str(payload.get("profile", "")),
            collection=str(payload.get("collection", "")),
            job_type=str(getattr(job, "job_type", "")),
            status=self._adapt_status(getattr(job, "status", "")),
            ordering_key=str(payload.get("ordering_key", "")) or None,
            idempotency_key=getattr(job, "idempotency_key", None),
            payload=payload,
            server_id=str(getattr(job, "host_id", "") or self.server_id),
            created_at=getattr(job, "created_at", datetime.now(timezone.utc)),
        )

    def _backend_job(self, job_id: str) -> Any:
        return self._backend.get(job_id)

    def get(self, job_id: str) -> JobRecord:
        """Execute get."""
        job = self._backend_job(job_id)
        if job is None:
            raise KeyError(job_id)
        return self._adapt_job(job)

    def list_jobs(self, limit: int | None = None) -> list[JobRecord]:
        """Execute list jobs."""
        jobs = [self._adapt_job(job) for job in self._backend.all_jobs()]
        jobs.sort(key=lambda item: (item.created_at, item.job_id), reverse=True)
        if limit is None:
            return jobs
        return jobs[: max(0, int(limit))]

    def _dispatch(self, job: JobRecord) -> None:
        callback = self._job_callbacks.pop(job.job_id, None)
        if callback is not None:
            callback(job)
            return
        handler = self._handlers.get(job.job_type)
        if handler is None:
            raise RuntimeError(f"No queue handler registered for job type: {job.job_type}")
        handler(job)

    def _run_handler(self, job: JobRecord) -> None:
        if self._timeout_seconds <= 0:
            self._dispatch(job)
            return
        started = time.monotonic()
        self._dispatch(job)
        elapsed = time.monotonic() - started
        if elapsed > float(self._timeout_seconds):  # pragma: no cover - timing dependent
            raise TimeoutError(f"Job timed out after {self._timeout_seconds}s")

    def _mark_retry_wait(self, job_id: str) -> None:
        _ = self._backend.update_status(job_id, PlatformJobStatus.RETRY_WAIT.value)
        time.sleep(max(0.0, self._retry_backoff_seconds))
        _ = self._backend.update_status(job_id, PlatformJobStatus.QUEUED.value)

    def _execute_backend_job(self, job_id: str) -> JobRecord:
        attempts = self._attempts.get(job_id, 0) + 1
        self._attempts[job_id] = attempts
        queued_job = self._backend_job(job_id)
        if queued_job is None:
            raise KeyError(job_id)
        local_job = self._adapt_job(queued_job)
        try:
            _ = self._backend.heartbeat(job_id)
            self._run_handler(local_job)
        except TimeoutError as exc:
            self._last_errors[job_id] = str(exc)
            if attempts < self._retry_max_attempts:
                self._mark_retry_wait(job_id)
                return self.get(job_id)
            _ = self._backend.update_status(job_id, PlatformJobStatus.TIMEOUT.value)
            raise
        except Exception as exc:
            self._last_errors[job_id] = str(exc)
            if attempts < self._retry_max_attempts:
                self._mark_retry_wait(job_id)
                return self.get(job_id)
            _ = self._backend.update_status(job_id, PlatformJobStatus.FAILED.value)
            raise
        _ = self._backend.update_status(job_id, PlatformJobStatus.SUCCEEDED.value)
        self._last_errors.pop(job_id, None)
        return self.get(job_id)

    def process_available(self, limit: int = 1) -> int:
        """Process the next available queued jobs."""
        processed = 0
        for queued_job in self._backend.dequeue(limit=max(1, int(limit))):
            if not self._backend.claim(queued_job.job_id, self.server_id, self._worker_id):
                continue
            _ = self._execute_backend_job(queued_job.job_id)
            processed += 1
        return processed

    def run(self, job_id: str, handler: Callable[[JobRecord], None] | None = None) -> JobRecord:
        """Execute run."""
        if handler is not None:
            self._job_callbacks[job_id] = handler

        while True:
            current = self.get(job_id)
            if current.status in {JobStatus.succeeded, JobStatus.cancelled}:
                return current
            if current.status in {JobStatus.failed, JobStatus.timeout}:
                message = self._last_errors.get(job_id, f"Job {job_id} failed")
                raise RuntimeError(message)
            if current.status is JobStatus.retry_wait:
                time.sleep(max(0.0, self._retry_backoff_seconds))
                continue
            if current.status is not JobStatus.queued:
                time.sleep(0.05)
                continue
            if not self._backend.claim(job_id, self.server_id, self._worker_id):
                time.sleep(0.05)
                continue
            try:
                result = self._execute_backend_job(job_id)
            except Exception:
                if self.get(job_id).status in {JobStatus.queued, JobStatus.retry_wait}:
                    continue
                raise
            if result.status is JobStatus.queued:
                continue
            return result

    def retry(self, job_id: str) -> JobRecord:
        """Reset a failed job back to queued state."""
        job = self.get(job_id)
        if job.status in {JobStatus.failed, JobStatus.timeout, JobStatus.cancelled}:
            _ = self._backend.update_status(job_id, PlatformJobStatus.QUEUED.value)
            self._attempts[job_id] = 0
        return self.get(job_id)

    def cancel(self, job_id: str) -> JobRecord:
        """Cancel a queued or completed job."""
        _ = self._backend.update_status(job_id, PlatformJobStatus.CANCELLED.value)
        return self.get(job_id)

    def queue_status(self) -> dict[str, Any]:
        """Return queue counters and backend identity."""
        counts = dict(self._backend.get_queue_status())
        return {
            "backend": self.backend_name(),
            "server_id": self.server_id,
            "total": sum(int(value) for value in counts.values()),
            "running": int(counts.get("running", 0)),
            "failed": int(counts.get("failed", 0)),
            "retry_wait": int(counts.get("retry_wait", 0)),
            "timeout": int(counts.get("timeout", 0)),
            "queue_depth": int(counts.get("queued", 0)),
            "active_jobs": int(counts.get("running", 0)),
            "worker_count": 1,
            "backend_healthy": (
                bool(self._job_queue.health())
                if self._job_queue is not None
                else bool(self._backend.health_check())
            ),
        }

    def backend_name(self) -> str:
        """Execute backend name."""
        return "cloud_dog_jobs"
