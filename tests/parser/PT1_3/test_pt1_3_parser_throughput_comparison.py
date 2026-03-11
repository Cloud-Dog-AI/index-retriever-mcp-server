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
