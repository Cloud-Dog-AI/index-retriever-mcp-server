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
from tests.w23a_helpers import corpus_file, parser_available, parser_skip_reason

pytestmark = pytest.mark.skipif(
    not parser_available("mineru"),
    reason=parser_skip_reason("mineru") or "mineru parser unavailable",
)


def _mineru_timeout_seconds() -> float:
    return float(os.getenv("MINERU_DOC_TIMEOUT_SECONDS", os.getenv("MINERU_TIMEOUT_SECONDS", "240")) or 240)
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_it2_9_mineru_parser_pdf_ir_output() -> None:
    # Use the smallest accepted real corpus PDF so the shared MinerU worker can
    # complete within its documented low-VRAM envelope.
    out = asyncio.run(
        asyncio.wait_for(
            parse_pdf_with_provider("mineru", source_path=corpus_file("fw9.pdf")),
            timeout=_mineru_timeout_seconds(),
        )
    )
    assert out["provider_id"] == "mineru"
    assert out["text_chars"] > 0
    assert out["source_uri"].startswith("file://")
    assert out["quality"]
