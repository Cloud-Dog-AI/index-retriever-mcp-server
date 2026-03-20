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

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """AuditEvent definition."""

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
    """IngestAuditEvent definition."""

    operation: str = "ingest"


class SearchAuditEvent(AuditEvent):
    """SearchAuditEvent definition."""

    operation: str = "search"


class DeleteAuditEvent(AuditEvent):
    """DeleteAuditEvent definition."""

    operation: str = "delete"


class AdminAuditEvent(AuditEvent):
    """AdminAuditEvent definition."""

    operation: str = "admin"
