# index-retriever-mcp-server — Audit Events
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Typed audit event models.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))  # noqa: UP017
    actor: str
    operation: str
    profile: str | None = None
    collection: str | None = None
    status: str = "success"
    request_id: str | None = None
    job_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class IngestAuditEvent(AuditEvent):
    operation: str = "ingest"


class SearchAuditEvent(AuditEvent):
    operation: str = "search"


class DeleteAuditEvent(AuditEvent):
    operation: str = "delete"


class AdminAuditEvent(AuditEvent):
    operation: str = "admin"
