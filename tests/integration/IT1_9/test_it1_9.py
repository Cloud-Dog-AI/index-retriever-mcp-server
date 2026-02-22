# index-retriever-mcp-server — IT1.9
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live Chroma contract CRUD test.

from tests.live_runtime import LiveIndexRuntime


def test_chroma_contract_test(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text(
        profile="default",
        collection="it_chroma",
        text="chroma contract data",
        source="api://it9",
        actor="integration",
        provider_id="chroma",
    )
    assert live_service.search("default", "it_chroma", "contract", provider_id="chroma")
    assert live_service.delete_by_id("default", "it_chroma", rec.record_id, provider_id="chroma") is True
