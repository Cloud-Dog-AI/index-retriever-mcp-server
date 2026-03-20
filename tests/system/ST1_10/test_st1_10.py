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

from datetime import datetime, timedelta, timezone

from tests.live_runtime import LiveIndexRuntime


def test_retention_cleanup(live_service: LiveIndexRuntime) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=120)  # noqa: UP017
    live_service.ingest_text(
        "default",
        "st_retention",
        "old record",
        "api://ret/old",
        actor="system",
        created_at=old,
    )
    live_service.ingest_text("default", "st_retention", "new record", "api://ret/new", actor="system")
    removed = live_service.retention_run("default", "st_retention", older_than_days=90)
    assert removed >= 1
