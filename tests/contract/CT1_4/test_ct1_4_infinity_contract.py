# index-retriever-mcp-server — CT1.4
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Infinity backend contract verification using cloud_dog_vdb adapters.

import pytest

from tests.live_runtime import LiveIndexRuntime


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
