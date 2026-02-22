# index-retriever-mcp-server — IT1.11
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live Ollama embedding provider verification.

from tests.live_runtime import LiveIndexRuntime


def test_embedding_provider_ollama(live_service: LiveIndexRuntime) -> None:
    vectors = live_service._run(
        live_service.llm_client.embed(
            ["live embedding dimension check"],
            provider_id=live_service.embedding_provider,
            model=live_service.embedding_model,
        )
    )
    assert len(vectors) == 1
    assert len(vectors[0]) in {768, 1024, 1536, 3072}
