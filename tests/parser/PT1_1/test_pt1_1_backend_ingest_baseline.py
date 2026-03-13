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
