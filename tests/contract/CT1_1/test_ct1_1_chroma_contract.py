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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")


def test_chroma_contract_crud(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text(
        profile="default",
        collection="ct_chroma",
        text="contract chroma payload",
        source="api://contract/chroma",
        actor="contract",
        provider_id="chroma",
    )
    rows = live_service.search("default", "ct_chroma", "payload", provider_id="chroma", top_k=5)
    assert rows
    assert live_service.delete_by_id("default", "ct_chroma", rec.record_id, provider_id="chroma") is True
