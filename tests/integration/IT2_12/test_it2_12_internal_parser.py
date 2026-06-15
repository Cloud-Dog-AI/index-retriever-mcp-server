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

from tests.integration.it2_matrix_helpers import parse_pdf_with_provider
import pytest
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_it2_12_internal_parser_pdf_ir_output() -> None:
    out = asyncio.run(parse_pdf_with_provider("internal"))
    assert out["provider_id"] == "internal"
    assert out["text_chars"] > 0
    assert out["source_uri"].startswith("file://")
    assert out["quality"]
