# index-retriever-mcp-server — UT1.25
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests query normalisation.

from index_tools.search.engine import normalise_query


def test_search_query_normalisation() -> None:
    assert normalise_query("  hello   world  ") == "hello world"
