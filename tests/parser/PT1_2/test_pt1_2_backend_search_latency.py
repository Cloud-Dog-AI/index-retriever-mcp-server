# index-retriever-mcp-server — PT1.2
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Search latency p50/p95/p99 baseline per available VDB backend.

from __future__ import annotations

import asyncio

import pytest

from tests.parser.pt1_helpers import available_backends, search_latency_for_provider, write_pt_artifact


@pytest.mark.timeout(1200)
def test_pt1_2_search_latency_baseline_per_backend() -> None:
    backends = available_backends()
    if not backends:
        pytest.skip("No VDB backends configured for PT1.2")

    matrix = []
    for provider_id in backends:
        result = asyncio.run(search_latency_for_provider(provider_id, queries=30))
        assert float(result["p50_ms"]) >= 0.0
        assert float(result["p95_ms"]) >= float(result["p50_ms"])
        assert float(result["p99_ms"]) >= float(result["p95_ms"])
        matrix.append(result)

    write_pt_artifact(
        "W23A-PT1.2-backend-search-latency.json",
        {
            "backends": backends,
            "matrix": matrix,
        },
    )
