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
