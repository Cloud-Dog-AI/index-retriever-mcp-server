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
