# index-retriever-mcp-server — IT2.12
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Internal parser provider baseline test on PDF corpus.

from __future__ import annotations

import asyncio

from tests.integration.it2_matrix_helpers import parse_pdf_with_provider


def test_it2_12_internal_parser_pdf_ir_output() -> None:
    out = asyncio.run(parse_pdf_with_provider("internal"))
    assert out["provider_id"] == "internal"
    assert out["text_chars"] > 0
    assert out["source_uri"].startswith("file://")
    assert out["quality"]
