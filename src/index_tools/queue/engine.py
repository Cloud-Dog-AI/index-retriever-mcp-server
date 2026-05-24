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
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from index_tools.queue.models import JobRecord, JobStatus


class JobCancelledError(RuntimeError):
    """Raised when cooperative job execution observes a cancellation request."""
from sqlalchemy import MetaData, create_engine, select, update
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


_UNSET = object()


_DB_SEP = "://"
_SQLITE_PROTO = f"sqlite{_DB_SEP}"


def _is_sqlite_database_url(database_url: str) -> bool:
    """Return whether the normalised queue database URL targets SQLite."""
    return database_url.startswith(_SQLITE_PROTO)


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
        database_path = getattr(engine.url, "database", None)
        if database_path and database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
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
        queue_wait_timeout_seconds: int | None = None,
        claim_timeout_seconds: int | None = None,
        retry_max_attempts: int | None = None,
        retry_backoff_seconds: float | None = None,
        redis_enabled: bool | None = None,
        redis_url: str | None = None,
        redis_key_prefix: str | None = None,
        audit_logger: Any | None = None,
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
        self._queue_wait_timeout_seconds = 1800 if queue_wait_timeout_seconds is None else int(queue_wait_timeout_seconds)
        self._claim_timeout_seconds = 60 if claim_timeout_seconds is None else int(claim_timeout_seconds)
        self._retry_max_attempts = 3 if retry_max_attempts is None else int(retry_max_attempts)
        self._retry_backoff_seconds = 5.0 if retry_backoff_seconds is None else float(retry_backoff_seconds)
        self._audit_logger = audit_logger
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

    def set_audit_logger(self, audit_logger: Any) -> None:
        """Bind the audit logger after service construction."""
        self._audit_logger = audit_logger

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)  # noqa: UP017

    @staticmethod
    def _serialise_datetime(value: Any) -> str | None:
        if value is None:
            return None
        if callable(getattr(value, "isoformat", None)):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value in {None, ""}:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    def _sql_repo(self) -> Any | None:
        return getattr(self._backend, "_repo", None)

    def _sql_row(self, job_id: str) -> dict[str, Any] | None:
        repo = self._sql_repo()
        if repo is None:
            return None
        with repo.engine.begin() as conn:
            row = conn.execute(select(repo.jobs).where(repo.jobs.c.job_id == job_id)).mappings().one_or_none()
        return dict(row) if row is not None else None

    def _sql_meta(self, job_id: str) -> dict[str, Any]:
        row = self._sql_row(job_id)
        if row is None:
            return {}
        meta = row.get("meta") or {}
        return dict(meta) if isinstance(meta, dict) else {}

    def _update_sql_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        meta_updates: dict[str, Any] | None = None,
        payload_updates: dict[str, Any] | None = None,
        clear_claim: bool | None = None,
        claimed_by: str | None = None,
    ) -> bool:
        repo = self._sql_repo()
        if repo is None:
            if status is not None:
                return bool(self._backend.update_status(job_id, status))
            return False
        with repo.engine.begin() as conn:
            row = conn.execute(
                select(repo.jobs.c.meta, repo.jobs.c.payload).where(repo.jobs.c.job_id == job_id)
            ).mappings().one_or_none()
            if row is None:
                return False
            meta = dict(row["meta"] or {})
            payload = dict(row["payload"] or {})
            if meta_updates:
                for key, value in meta_updates.items():
                    meta[key] = value
            if payload_updates:
                for key, value in payload_updates.items():
                    payload[key] = value
            values: dict[str, Any] = {
                "updated_at": self._now(),
                "meta": meta,
                "payload": payload,
            }
            if status is not None:
                values["status"] = status
            if clear_claim is True:
                values["claimed_by"] = None
            elif claimed_by is not None:
                values["claimed_by"] = claimed_by
            result = conn.execute(update(repo.jobs).where(repo.jobs.c.job_id == job_id).values(**values))
        return result.rowcount == 1

    def _emit_audit_event(
        self,
        job: JobRecord,
        *,
        action: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        if self._audit_logger is None:
            return
        build_event = getattr(self._audit_logger, "build_event", None)
        write_event = getattr(self._audit_logger, "write_event", None)
        actor_builder = getattr(self._audit_logger, "_actor", None)
        target_builder = getattr(self._audit_logger, "_target", None)
        if not callable(build_event) or not callable(write_event) or not callable(actor_builder) or not callable(target_builder):
            return
        actor_id = str(job.payload.get("actor") or job.user_id or "system")
        actor_roles = {"writer"} if actor_id not in {"system", "service"} else {"system"}
        event = build_event(
            event_type="job.lifecycle",
            actor=actor_builder(actor_id, roles=actor_roles),
            action=action,
            outcome=outcome,
            target=target_builder("job", job.job_id, target_name=job.job_type),
            details={
                "job_id": job.job_id,
                "job_type": job.job_type,
                "profile": job.profile,
                "collection": job.collection,
                "status": job.status.value,
                "attempt": job.attempt,
                "max_attempts": job.max_attempts,
                "progress": job.progress,
                "server_id": job.server_id,
                **(details or {}),
            },
        )
        write_event(event)

    def _transition(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        phase: str | None = None,
        percentage: float | None = None,
        message: str | None = None,
        attempt: int | None = None,
        max_attempts: int | None = None,
        next_run_at: datetime | object | None = _UNSET,
        started_at: datetime | object | None = _UNSET,
        finished_at: datetime | object | None = _UNSET,
        last_heartbeat_at: datetime | object | None = _UNSET,
        last_error: dict[str, Any] | object | None = _UNSET,
        result_ref: str | object | None = _UNSET,
        clear_claim: bool | None = None,
        claimed_by: str | None = None,
        audit_action: str | None = None,
        extra_progress: dict[str, Any] | None = None,
    ) -> JobRecord:
        current = self.get(job_id)
        history = list(current.progress.get("events", [])) if isinstance(current.progress, dict) else []
        if phase is not None:
            history.append(
                {
                    "phase": phase,
                    "percentage": percentage,
                    "message": message or "",
                    "timestamp": self._serialise_datetime(self._now()),
                }
            )
            history = history[-12:]
        progress = dict(current.progress)
        if phase is not None:
            progress.update(
                {
                    "phase": phase,
                    "percentage": percentage,
                    "message": message or "",
                    "events": history,
                }
            )
        if extra_progress:
            progress.update(extra_progress)
        meta_updates = {
            "attempt": current.attempt if attempt is None else int(attempt),
            "max_attempts": current.max_attempts if max_attempts is None else int(max_attempts),
            "next_run_at": self._serialise_datetime(current.next_run_at) if next_run_at is _UNSET else self._serialise_datetime(next_run_at),
            "started_at": self._serialise_datetime(current.started_at) if started_at is _UNSET else self._serialise_datetime(started_at),
            "finished_at": self._serialise_datetime(current.finished_at) if finished_at is _UNSET else self._serialise_datetime(finished_at),
            "last_heartbeat_at": self._serialise_datetime(current.last_heartbeat_at) if last_heartbeat_at is _UNSET else self._serialise_datetime(last_heartbeat_at),
            "last_error": current.last_error if last_error is _UNSET else last_error,
            "result_ref": current.result_ref if result_ref is _UNSET else result_ref,
            "progress": progress,
            "run_timeout_ms": self._timeout_seconds * 1000,
            "claim_timeout_ms": self._claim_timeout_seconds * 1000,
        }
        self._update_sql_job(
            job_id,
            status=status.value if status is not None else None,
            meta_updates=meta_updates,
            clear_claim=clear_claim,
            claimed_by=claimed_by,
        )
        updated = self.get(job_id)
        if audit_action is not None:
            self._emit_audit_event(
                updated,
                action=audit_action,
                outcome="success" if updated.status not in {JobStatus.failed, JobStatus.dead_lettered, JobStatus.timeout} else "failure",
                details={"previous_status": current.status.value},
            )
        return updated

    @staticmethod
    def _normalise_database_url(database_url: str | None) -> str:
        raw = (database_url or "").strip()
        if not raw:
            return ""
        # URL scheme rewrites: async dialect → sync dialect.
        _rewrites = {
            f"sqlite+aiosqlite{_DB_SEP}": f"sqlite{_DB_SEP}",
            f"postgresql+asyncpg{_DB_SEP}": f"postgresql+psycopg{_DB_SEP}",
        }
        for async_prefix, sync_prefix in _rewrites.items():
            if raw.startswith(async_prefix):
                return sync_prefix + raw[len(async_prefix):]
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
        now = job.created_at
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
            status=PlatformJobStatus.CREATED,
            priority=int(priority),
            created_at=now,
            updated_at=now,
            tenant_id=job.profile,
            host_id=self.server_id,
            idempotency_key=job.idempotency_key,
            user_id=actor,
            request_source=str(payload_data.get("source", "")) or None,
            max_attempts=self._retry_max_attempts,
            progress={"phase": "created", "percentage": 0, "message": "job created"},
            run_timeout_ms=self._timeout_seconds * 1000,
            claim_timeout_ms=self._claim_timeout_seconds * 1000,
        )
        self._backend.enqueue(queued_job)
        self._transition(
            job.job_id,
            status=JobStatus.validated,
            phase="validated",
            percentage=5,
            message="job payload validated",
            max_attempts=self._retry_max_attempts,
            audit_action="validate",
        )
        return self._transition(
            job.job_id,
            status=JobStatus.queued,
            phase="queued",
            percentage=10,
            message="job queued",
            max_attempts=self._retry_max_attempts,
            audit_action="queue",
        )

    def _adapt_status(self, value: Any) -> JobStatus:
        raw = str(getattr(value, "value", value)).strip().lower()
        for candidate in JobStatus:
            if candidate.value == raw:
                return candidate
        return JobStatus.failed

    def _adapt_job(self, job: Any) -> JobRecord:
        row = self._sql_row(str(job.job_id))
        meta = dict(row.get("meta") or {}) if isinstance(row, dict) else {}
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
            updated_at=getattr(job, "updated_at", None),
            started_at=self._parse_datetime(meta.get("started_at") or getattr(job, "started_at", None)),
            finished_at=self._parse_datetime(meta.get("finished_at") or getattr(job, "finished_at", None)),
            next_run_at=self._parse_datetime(meta.get("next_run_at") or getattr(job, "next_run_at", None)),
            last_heartbeat_at=self._parse_datetime(meta.get("last_heartbeat_at") or getattr(job, "last_heartbeat_at", None)),
            attempt=int(meta.get("attempt", getattr(job, "attempt", 0)) or 0),
            max_attempts=int(meta.get("max_attempts", getattr(job, "max_attempts", self._retry_max_attempts)) or self._retry_max_attempts),
            claimed_by=str(getattr(job, "claimed_by", "") or "") or None,
            correlation_id=meta.get("correlation_id") or getattr(job, "correlation_id", None),
            trace_id=meta.get("trace_id") or getattr(job, "trace_id", None),
            user_id=meta.get("user_id") or getattr(job, "user_id", None),
            request_source=meta.get("request_source") or getattr(job, "request_source", None),
            request_ip=meta.get("request_ip") or getattr(job, "request_ip", None),
            request_auth_method=meta.get("request_auth_method") or getattr(job, "request_auth_method", None),
            request_auth_identity=meta.get("request_auth_identity") or getattr(job, "request_auth_identity", None),
            request_user_agent=meta.get("request_user_agent") or getattr(job, "request_user_agent", None),
            last_error=meta.get("last_error") or getattr(job, "last_error", None),
            result_ref=meta.get("result_ref") or getattr(job, "result_ref", None),
            progress=dict(meta.get("progress") or getattr(job, "progress", {}) or {}),
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
        next_run_at = self._now() + timedelta(seconds=max(0.0, self._retry_backoff_seconds))
        self._transition(
            job_id,
            status=JobStatus.retry_wait,
            phase="retry_wait",
            percentage=25,
            message="job waiting before retry",
            next_run_at=next_run_at,
            clear_claim=True,
            audit_action="retry_wait",
        )
        time.sleep(max(0.0, self._retry_backoff_seconds))
        self._transition(
            job_id,
            status=JobStatus.queued,
            phase="queued",
            percentage=10,
            message="job re-queued after backoff",
            next_run_at=None,
            clear_claim=True,
            audit_action="requeue",
        )

    def _execute_backend_job(self, job_id: str) -> JobRecord:
        attempts = self.get(job_id).attempt + 1
        queued_job = self._backend_job(job_id)
        if queued_job is None:
            raise KeyError(job_id)
        local_job = self._transition(
            job_id,
            status=JobStatus.running,
            phase="running",
            percentage=20,
            message="job handler started",
            attempt=attempts,
            max_attempts=self._retry_max_attempts,
            started_at=self._now(),
            last_heartbeat_at=self._now(),
            claimed_by=f"{self.server_id}:{self._worker_id}",
            clear_claim=False,
            audit_action="start",
        )
        try:
            _ = self._backend.heartbeat(job_id)
            self._run_handler(local_job)
        except JobCancelledError:
            current = self.get(job_id)
            if current.status is not JobStatus.cancelled:
                return self.cancel(job_id)
            return current
        except TimeoutError as exc:
            if self.get(job_id).status is JobStatus.cancelled:
                return self.get(job_id)
            error_payload = {"type": "timeout", "message": str(exc), "attempt": attempts}
            if attempts < self._retry_max_attempts:
                self._last_errors[job_id] = str(exc)
                self._mark_retry_wait(job_id)
                return self.get(job_id)
            self._transition(
                job_id,
                status=JobStatus.dead_lettered,
                phase="dead_lettered",
                percentage=100,
                message="job dead-lettered after timeout exhaustion",
                attempt=attempts,
                finished_at=self._now(),
                last_error=error_payload,
                clear_claim=True,
                audit_action="dead_letter",
            )
            raise
        except Exception as exc:
            if self.get(job_id).status is JobStatus.cancelled:
                return self.get(job_id)
            error_payload: dict[str, Any] = {"type": type(exc).__name__, "message": str(exc), "attempt": attempts}
            # W28D-440E1: include structured details from EmbeddingBatchError
            if hasattr(exc, "to_error_details") and callable(exc.to_error_details):
                error_payload["details"] = exc.to_error_details()
            if attempts < self._retry_max_attempts:
                self._last_errors[job_id] = str(exc)
                self._mark_retry_wait(job_id)
                return self.get(job_id)
            self._transition(
                job_id,
                status=JobStatus.dead_lettered,
                phase="dead_lettered",
                percentage=100,
                message="job dead-lettered after retry exhaustion",
                attempt=attempts,
                finished_at=self._now(),
                last_error=error_payload,
                clear_claim=True,
                audit_action="dead_letter",
            )
            raise
        if self.get(job_id).status is JobStatus.cancelled:
            return self.get(job_id)
        self._transition(
            job_id,
            status=JobStatus.succeeded,
            phase="succeeded",
            percentage=100,
            message="job completed successfully",
            attempt=attempts,
            finished_at=self._now(),
            clear_claim=True,
            audit_action="complete",
        )
        self._last_errors.pop(job_id, None)
        return self.get(job_id)

    def process_available(self, limit: int = 1) -> int:
        """Process the next available queued jobs."""
        processed = 0
        for queued_job in self._backend.dequeue(limit=max(1, int(limit))):
            if not self._backend.claim(queued_job.job_id, self.server_id, self._worker_id):
                continue
            self._transition(
                queued_job.job_id,
                status=JobStatus.dispatched,
                phase="dispatched",
                percentage=15,
                message="job claimed by worker",
                clear_claim=False,
                claimed_by=f"{self.server_id}:{self._worker_id}",
                audit_action="dispatch",
            )
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
            if current.status in {JobStatus.failed, JobStatus.timeout, JobStatus.dead_lettered}:
                message = self._last_errors.get(job_id, f"Job {job_id} failed")
                raise RuntimeError(message)
            if current.status is JobStatus.retry_wait:
                if current.next_run_at is not None:
                    wait_seconds = max(0.0, (current.next_run_at - self._now()).total_seconds())
                    time.sleep(min(wait_seconds, max(0.0, self._retry_backoff_seconds)))
                else:
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
        if job.status in {JobStatus.failed, JobStatus.timeout, JobStatus.cancelled, JobStatus.dead_lettered}:
            self._attempts[job_id] = 0
            self._transition(
                job_id,
                status=JobStatus.queued,
                phase="queued",
                percentage=10,
                message="job re-queued for retry",
                attempt=0,
                next_run_at=None,
                started_at=None,
                finished_at=None,
                last_error=None,
                clear_claim=True,
                audit_action="retry",
            )
        return self.get(job_id)

    def cancel(self, job_id: str) -> JobRecord:
        """Cancel a queued or completed job."""
        return self._transition(
            job_id,
            status=JobStatus.cancelled,
            phase="cancelled",
            percentage=100,
            message="job cancelled",
            finished_at=self._now(),
            clear_claim=True,
            audit_action="cancel",
        )

    def wait(self, job_id: str, timeout_seconds: int | None = None) -> JobRecord:
        """Block until the job reaches a terminal state or timeout expires."""
        deadline = time.monotonic() + float(self._queue_wait_timeout_seconds if timeout_seconds is None else timeout_seconds)
        while True:
            current = self.get(job_id)
            if current.status in {JobStatus.succeeded, JobStatus.cancelled, JobStatus.failed, JobStatus.timeout, JobStatus.dead_lettered}:
                return current
            if time.monotonic() >= deadline:
                return current
            time.sleep(0.1)

    def record_progress(
        self,
        job_id: str,
        *,
        phase: str,
        percentage: float,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> JobRecord:
        """Persist a progress checkpoint for the active job."""
        return self._transition(
            job_id,
            phase=phase,
            percentage=percentage,
            message=message,
            last_heartbeat_at=self._now(),
            clear_claim=False,
            extra_progress=extra,
            audit_action="progress",
        )

    def queue_status(self) -> dict[str, Any]:
        """Return queue counters and backend identity."""
        counts = dict(self._backend.get_queue_status())
        return {
            "backend": self.backend_name(),
            "server_id": self.server_id,
            "total": sum(int(value) for value in counts.values()),
            "created": int(counts.get("created", 0)),
            "validated": int(counts.get("validated", 0)),
            "dispatched": int(counts.get("dispatched", 0)),
            "running": int(counts.get("running", 0)),
            "failed": int(counts.get("failed", 0)),
            "dead_lettered": int(counts.get("dead_lettered", 0)),
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
