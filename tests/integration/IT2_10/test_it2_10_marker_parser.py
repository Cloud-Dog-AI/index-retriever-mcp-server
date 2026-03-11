# index-retriever-mcp-server — IT2.10
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Real Marker MCP parser provider test on PDF corpus.

from __future__ import annotations

import asyncio
import os

import pytest

from tests.integration.it2_matrix_helpers import parse_pdf_with_provider
from tests.w23a_helpers import parser_available, parser_skip_reason

pytestmark = pytest.mark.skipif(
    not parser_available("marker_mcp"),
    reason=parser_skip_reason("marker_mcp") or "marker_mcp parser unavailable",
)


def _marker_timeout_seconds() -> float:
    configured = float(os.getenv("MARKER_MCP_DOC_TIMEOUT_SECONDS", os.getenv("MARKER_MCP_TIMEOUT_SECONDS", "1200")) or 1200)
    return max(360.0, configured)


def test_it2_10_marker_parser_pdf_ir_output() -> None:
    out = asyncio.run(asyncio.wait_for(parse_pdf_with_provider("marker_mcp"), timeout=_marker_timeout_seconds()))
    assert out["provider_id"] == "marker_mcp"
    assert out["text_chars"] > 0
    assert out["source_uri"].startswith("file://")
    assert out["quality"]
