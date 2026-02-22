# index-retriever-mcp-server — CT1.2
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live Qdrant contract verification using cloud_dog_vdb adapters.

from tests.live_runtime import LiveIndexRuntime


def test_qdrant_contract_crud(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text(
        profile="default",
        collection="ct_qdrant",
        text="contract qdrant payload",
        source="api://contract/qdrant",
        actor="contract",
        provider_id="qdrant",
    )
    rows = live_service.search("default", "ct_qdrant", "payload", provider_id="qdrant", top_k=5)
    assert rows
    assert live_service.delete_by_id("default", "ct_qdrant", rec.record_id, provider_id="qdrant") is True
