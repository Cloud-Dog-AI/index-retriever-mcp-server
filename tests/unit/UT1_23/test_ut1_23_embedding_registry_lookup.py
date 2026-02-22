# index-retriever-mcp-server — UT1.23
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests embedding registry lookup.

from index_tools.embeddings.registry import EmbeddingRegistry


def test_embedding_registry_lookup() -> None:
    registry = EmbeddingRegistry()
    registry.register("default", lambda texts: [[1.0] for _ in texts])
    fn = registry.get("default")
    assert fn(["a", "b"]) == [[1.0], [1.0]]
