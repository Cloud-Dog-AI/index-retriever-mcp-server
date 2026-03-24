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
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):  # noqa: UP042
    """JobStatus definition."""

    queued = "queued"
    running = "running"
    retry_wait = "retry_wait"
    timeout = "timeout"
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
    payload: dict[str, Any] = Field(default_factory=dict)
    server_id: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))  # noqa: UP017
