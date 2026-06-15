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


def test_search_top_k(live_service: LiveIndexRuntime) -> None:
    for i in range(4):
        live_service.ingest_text("default", "st_topk", f"shared token {i}", f"api://topk/{i}", actor="system")
    rows = live_service.search("default", "st_topk", "shared", top_k=2)
    assert len(rows) == 2
