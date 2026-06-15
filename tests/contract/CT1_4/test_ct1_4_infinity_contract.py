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

import pytest

from tests.live_runtime import LiveIndexRuntime
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")


def test_infinity_contract_crud(live_service: LiveIndexRuntime) -> None:
    if "infinity" not in live_service._enabled_providers:
        pytest.fail("BLOCKED: infinity provider not configured in live runtime")
    if not live_service.backend_health_check(provider_id="infinity"):
        pytest.fail("BLOCKED: infinity provider health check failed")

    rec = live_service.ingest_text(
        profile="default",
        collection="ct_infinity",
        text="contract infinity payload",
        source="api://contract/infinity",
        actor="contract",
        provider_id="infinity",
    )
    rows = live_service.search("default", "ct_infinity", "payload", provider_id="infinity", top_k=5)
    assert rows
    assert live_service.delete_by_id("default", "ct_infinity", rec.record_id, provider_id="infinity") is True
