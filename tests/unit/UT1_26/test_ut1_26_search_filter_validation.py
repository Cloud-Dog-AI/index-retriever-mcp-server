# index-retriever-mcp-server — UT1.26
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests search filter validation.

import pytest

from index_tools.search.engine import validate_filters


def test_search_filter_validation() -> None:
    assert validate_filters({"tenant": "a", "count": 1})["count"] == 1
    with pytest.raises(ValueError):
        validate_filters({"bad": [1, 2]})
