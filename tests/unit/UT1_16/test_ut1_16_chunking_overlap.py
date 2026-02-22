# index-retriever-mcp-server — UT1.16
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests chunk overlap behaviour.

from index_tools.pipeline.chunking import token_chunks


def test_chunking_overlap() -> None:
    chunks = token_chunks("one two three four", chunk_size=2, chunk_overlap=1)
    assert chunks[0] == "one two"
    assert chunks[1].startswith("two")
