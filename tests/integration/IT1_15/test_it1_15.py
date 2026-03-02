# index-retriever-mcp-server — IT1.15
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Infinity adapter contract path (strict: BLOCKED if provider unavailable).

import pytest

from tests.live_runtime import LiveIndexRuntime


def test_infinity_adapter_contract_path(live_service: LiveIndexRuntime) -> None:
    if "infinity" not in live_service._enabled_providers:
        pytest.fail("BLOCKED: infinity provider not configured in live runtime")
    if not live_service.backend_health_check(provider_id="infinity"):
        pytest.fail("BLOCKED: infinity provider health check failed")

    rec = live_service.ingest_text(
        profile="default",
        collection="it_infinity_contract",
        text="infinity contract payload",
        source="api://it/infinity",
        actor="integration",
        provider_id="infinity",
    )
    rows = live_service.search("default", "it_infinity_contract", "contract", provider_id="infinity", top_k=5)
    assert rows
    assert live_service.delete_by_id("default", "it_infinity_contract", rec.record_id, provider_id="infinity") is True
