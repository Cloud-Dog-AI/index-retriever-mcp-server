# @pytest.mark.AT
# @pytest.mark.internal
# @pytest.mark.probe
# PS-REQ-TEST-TRACE marker anchor for structural conformance.

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

import pytest

from tests.integration.it2_matrix_helpers import parse_pdf_with_provider
from tests.w23a_helpers import corpus_file, parser_available, write_artifact_json


@pytest.mark.timeout(600)
def test_at2_3_multi_parser_quality_matrix() -> None:
    providers = [
        provider_id
        for provider_id in ("deepdoc", "docling", "mineru", "transformers", "internal")
        if parser_available(provider_id)
    ]
    if len(providers) < 2:
        pytest.fail("Insufficient parser providers configured for quality comparison", pytrace=False)

    source = corpus_file("Examples.pdf", "NIST.SP.800-53r5.pdf")
    matrix: list[dict[str, object]] = []
    for provider_id in providers:
        out = asyncio.run(parse_pdf_with_provider(provider_id, source_path=source))
        matrix.append(
            {
                "provider_id": provider_id,
                "text_chars": int(out["text_chars"]),
                "text_blocks": int(out["text_blocks"]),
                "table_blocks": int(out["table_blocks"]),
                "quality": dict(out["quality"]),
            }
        )

    assert matrix
    assert all(int(entry["text_chars"]) > 0 for entry in matrix)
    _ = write_artifact_json(
        "W23A-AT2.3-parser-quality-matrix.json",
        {
            "file": source.name,
            "providers": providers,
            "matrix": matrix,
        },
    )
