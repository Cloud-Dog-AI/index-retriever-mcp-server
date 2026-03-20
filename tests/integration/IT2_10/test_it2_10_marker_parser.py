# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
