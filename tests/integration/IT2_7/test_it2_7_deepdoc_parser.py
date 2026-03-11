# index-retriever-mcp-server — IT2.7
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Real DeepDoc parser provider test on PDF corpus.

from __future__ import annotations

import asyncio

import pytest

from tests.integration.it2_matrix_helpers import parse_pdf_with_provider
from tests.w23a_helpers import parser_available, parser_skip_reason

pytestmark = pytest.mark.skipif(
    not parser_available("deepdoc"),
    reason=parser_skip_reason("deepdoc") or "deepdoc parser unavailable",
)


def test_it2_7_deepdoc_parser_pdf_ir_output() -> None:
    out = asyncio.run(parse_pdf_with_provider("deepdoc"))
    assert out["provider_id"] == "deepdoc"
    assert out["text_chars"] > 0
    assert out["source_uri"].startswith("file://")
    assert out["quality"]
