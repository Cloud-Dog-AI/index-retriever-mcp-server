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

# index-retriever-mcp-server — PT1.3
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Parser throughput comparison across available parser providers.

from __future__ import annotations

import pytest

from tests.parser.pt1_helpers import available_parsers, parser_throughput_case, write_pt_artifact


@pytest.mark.timeout(1200)
def test_pt1_3_parser_throughput_comparison() -> None:
    providers = available_parsers()
    if len(providers) < 2:
        pytest.skip("Insufficient parser providers configured for PT1.3")

    matrix = []
    for provider_id in providers:
        result = parser_throughput_case(provider_id)
        assert float(result["elapsed_seconds"]) > 0.0
        assert int(result["text_chars"]) > 0
        matrix.append(result)

    write_pt_artifact(
        "W23A-PT1.3-parser-throughput.json",
        {
            "providers": providers,
            "matrix": matrix,
        },
    )
