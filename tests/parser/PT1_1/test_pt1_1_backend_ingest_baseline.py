# index-retriever-mcp-server — PT1.1
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Ingest baseline (10 documents) per available VDB backend.

from __future__ import annotations

import asyncio

import pytest

from tests.parser.pt1_helpers import available_backends, ingest_baseline_for_provider, write_pt_artifact


@pytest.mark.timeout(1200)
def test_pt1_1_ingest_baseline_per_backend() -> None:
    backends = available_backends()
    if not backends:
        pytest.skip("No VDB backends configured for PT1.1")

    matrix = []
    for provider_id in backends:
        result = asyncio.run(ingest_baseline_for_provider(provider_id, documents=10))
        assert int(result["count"]) == 10
        matrix.append(result)

    write_pt_artifact(
        "W23A-PT1.1-backend-ingest-baseline.json",
        {
            "backends": backends,
            "matrix": matrix,
        },
    )
