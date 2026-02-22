# index-retriever-mcp-server — UT1.13
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests PDF extraction helper.

from index_tools.convert.pdf import extract_text


def test_convert_pdf_extract() -> None:
    assert "sample" in extract_text(b"sample pdf text")
