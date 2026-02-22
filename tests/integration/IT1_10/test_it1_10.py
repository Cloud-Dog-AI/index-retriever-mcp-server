# index-retriever-mcp-server — IT1.10
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live Qdrant contract CRUD test.

from tests.live_runtime import LiveIndexRuntime


def test_qdrant_contract_test(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text(
        profile="default",
        collection="it_qdrant",
        text="qdrant contract data",
        source="api://it10",
        actor="integration",
        provider_id="qdrant",
    )
    rows = live_service.search("default", "it_qdrant", "contract", provider_id="qdrant")
    assert rows
    assert live_service.delete_by_id("default", "it_qdrant", rec.record_id, provider_id="qdrant") is True
