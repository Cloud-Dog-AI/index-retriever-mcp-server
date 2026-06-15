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

from tests.live_runtime import LiveIndexRuntime
import pytest
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.req("FR-005")


def test_search_metadata_filter(live_service: LiveIndexRuntime) -> None:
    live_service.ingest_text(
        "default",
        "st_filter",
        "tenant alpha entry",
        "api://alpha",
        actor="system",
        provider_id="qdrant",
        metadata={"tenant": "alpha"},
    )
    live_service.ingest_text(
        "default",
        "st_filter",
        "tenant beta entry",
        "api://beta",
        actor="system",
        provider_id="qdrant",
        metadata={"tenant": "beta"},
    )
    rows = live_service.search("default", "st_filter", "entry", provider_id="qdrant", filters={"tenant": "alpha"})
    assert rows
    assert all(r["metadata"].get("tenant") == "alpha" for r in rows)
