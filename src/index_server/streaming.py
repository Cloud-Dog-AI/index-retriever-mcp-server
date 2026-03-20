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

from typing import Any

from index_tools.tools.service import IndexService


def ingest_stream_open(service: IndexService, profile: str, collection: str, ordering_key: str) -> dict[str, str]:
    """Execute ingest stream open."""
    session_id = service.ingest_stream_open(profile=profile, collection=collection, ordering_key=ordering_key)
    return {"session_id": session_id}


def ingest_stream_event(
    service: IndexService,
    session_id: str,
    text: str,
    actor: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Execute ingest stream event."""
    job_id = service.ingest_stream_event(session_id=session_id, text=text, actor=actor, metadata=metadata)
    return {"job_id": job_id}


def ingest_stream_close(service: IndexService, session_id: str) -> dict[str, Any]:
    """Execute ingest stream close."""
    return service.ingest_stream_close(session_id=session_id)
