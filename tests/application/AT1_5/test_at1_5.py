# index-retriever-mcp-server — AT1.5
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live multi-backend workflow across Chroma and Qdrant.

from tests.live_runtime import LiveIndexRuntime


def test_full_workflow_multi_backend_switch(live_service: LiveIndexRuntime) -> None:
    _ = live_service.ingest_text(
        "default",
        "at_multi_chroma",
        "chroma backend payload",
        "api://at/chroma",
        actor="application",
        provider_id="chroma",
    )
    _ = live_service.ingest_text(
        "default",
        "at_multi_qdrant",
        "qdrant backend payload",
        "api://at/qdrant",
        actor="application",
        provider_id="qdrant",
    )
    assert live_service.search("default", "at_multi_chroma", "payload", provider_id="chroma")
    assert live_service.search("default", "at_multi_qdrant", "payload", provider_id="qdrant")
