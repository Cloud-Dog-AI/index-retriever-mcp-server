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

# index-retriever-mcp-server — IT1.14
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Capability-aware backend planning including unsupported-filter negative path.

import pytest

from tests.live_runtime import LiveIndexRuntime


def test_capability_aware_backend_planning(live_service: LiveIndexRuntime) -> None:
    capabilities = live_service.backend_capabilities("chroma")
    plan = live_service.plan_search(
        provider_id="chroma",
        query="planner token",
        top_k=50_000,
        filters={"tenant_id": "default"},
    )
    assert plan["mode"] in {"vector", "hybrid"}
    assert int(plan["top_k"]) <= int(capabilities["max_batch_size"])
    assert plan["filters"].get("tenant_id") == "default"

    with pytest.raises(ValueError):
        live_service.plan_search(
            provider_id="chroma",
            query="planner token",
            top_k=10,
            filters={"tenant_id": "default"},
            capability_override={"filtering": False},
        )
