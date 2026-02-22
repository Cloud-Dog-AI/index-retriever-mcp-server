# index-retriever-mcp-server — UT1.15
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests token chunking strategy.

from index_tools.pipeline.chunking import token_chunks


def test_chunking_token_strategy() -> None:
    chunks = token_chunks("a b c d e f", chunk_size=3, chunk_overlap=1)
    assert chunks == ["a b c", "c d e", "e f"]
