# index-retriever-mcp-server — CT1.3
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Contract parity check across Chroma and Qdrant backends.

from tests.live_runtime import LiveIndexRuntime


def test_backend_contract_parity(live_service: LiveIndexRuntime) -> None:
    _ = live_service.ingest_text(
        profile="default",
        collection="ct_parity_chroma",
        text="parity data token",
        source="api://contract/parity/chroma",
        actor="contract",
        provider_id="chroma",
    )
    _ = live_service.ingest_text(
        profile="default",
        collection="ct_parity_qdrant",
        text="parity data token",
        source="api://contract/parity/qdrant",
        actor="contract",
        provider_id="qdrant",
    )

    chroma_rows = live_service.search("default", "ct_parity_chroma", "parity", provider_id="chroma", top_k=3)
    qdrant_rows = live_service.search("default", "ct_parity_qdrant", "parity", provider_id="qdrant", top_k=3)

    assert chroma_rows
    assert qdrant_rows
    assert isinstance(chroma_rows[0].get("metadata"), dict)
    assert isinstance(qdrant_rows[0].get("metadata"), dict)
