# index-retriever-mcp-server — CT1.1
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live Chroma contract verification using cloud_dog_vdb client.

from tests.live_runtime import LiveIndexRuntime


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
