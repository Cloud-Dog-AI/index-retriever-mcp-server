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
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.req("FR-004")


def test_full_workflow_multi_backend_switch(live_service: LiveIndexRuntime) -> None:
    _ = live_service.ingest_text(
        "default",
        "at_multi_chroma",
        "chroma backend payload",
        "api://at/chroma",
        actor="application",
        provider_id="chroma",
    )
    _ = live_service.ingest_text(
        "default",
        "at_multi_qdrant",
        "qdrant backend payload",
        "api://at/qdrant",
        actor="application",
        provider_id="qdrant",
    )
    assert live_service.search("default", "at_multi_chroma", "payload", provider_id="chroma")
    assert live_service.search("default", "at_multi_qdrant", "payload", provider_id="qdrant")
