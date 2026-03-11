# index-retriever-mcp-server — Job Models
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Queue and job models aligned with cloud_dog_jobs semantics.

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):  # noqa: UP042
    """JobStatus definition."""

    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class JobRecord(BaseModel):
    """JobRecord definition."""

    job_id: str
    profile: str
    collection: str
    job_type: str
    status: JobStatus = JobStatus.queued
    ordering_key: str | None = None
    idempotency_key: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))  # noqa: UP017
