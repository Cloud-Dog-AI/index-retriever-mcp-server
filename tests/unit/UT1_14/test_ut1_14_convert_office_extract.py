# index-retriever-mcp-server — UT1.14
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests Office extraction helper.

from index_tools.convert.office import extract_text


def test_convert_office_extract() -> None:
    assert "sheet" in extract_text(b"sheet data")
