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

# index-retriever-mcp-server — AT1.4
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live retention policy workflow.

from datetime import datetime, timedelta, timezone

from tests.live_runtime import LiveIndexRuntime


def test_full_workflow_retention_enforcement(live_service: LiveIndexRuntime) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=365)  # noqa: UP017
    _ = live_service.ingest_text(
        "default",
        "at_retention",
        "old payload",
        "api://at/old",
        actor="application",
        created_at=old,
    )
    _ = live_service.ingest_text("default", "at_retention", "new payload", "api://at/new", actor="application")
    removed = live_service.retention_run("default", "at_retention", older_than_days=90)
    assert removed >= 1
