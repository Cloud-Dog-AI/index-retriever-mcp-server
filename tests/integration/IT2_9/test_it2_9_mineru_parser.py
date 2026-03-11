# index-retriever-mcp-server — IT2.9
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Real MinerU parser provider test on PDF corpus.

from __future__ import annotations

import asyncio
import os

import pytest

from tests.integration.it2_matrix_helpers import parse_pdf_with_provider
from tests.w23a_helpers import parser_available, parser_skip_reason

pytestmark = pytest.mark.skipif(
    not parser_available("mineru"),
    reason=parser_skip_reason("mineru") or "mineru parser unavailable",
)


def _mineru_timeout_seconds() -> float:
    return float(os.getenv("MINERU_DOC_TIMEOUT_SECONDS", os.getenv("MINERU_TIMEOUT_SECONDS", "240")) or 240)


def test_it2_9_mineru_parser_pdf_ir_output() -> None:
    out = asyncio.run(asyncio.wait_for(parse_pdf_with_provider("mineru"), timeout=_mineru_timeout_seconds()))
    assert out["provider_id"] == "mineru"
    assert out["text_chars"] > 0
    assert out["source_uri"].startswith("file://")
    assert out["quality"]
