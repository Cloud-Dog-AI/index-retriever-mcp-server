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

from tests.w23a_helpers import (
    VDB_PROVIDER_IDS,
    backend_available,
    parser_available,
    run_backend_parser_pipeline,
    write_artifact_json,
)
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.req("FR-004")


@pytest.mark.timeout(900)
def test_at2_5_full_pipeline_e2e_per_available_backend() -> None:
    available_backends = [provider_id for provider_id in VDB_PROVIDER_IDS if backend_available(provider_id)]
    if not available_backends:
        pytest.fail("No VDB backends configured for AT2.5", pytrace=False)

    parser_chain = ["mineru", "internal"] if parser_available("mineru") else ["internal"]

    results: list[dict[str, object]] = []
    for provider_id in available_backends:
        payload = asyncio.run(
            run_backend_parser_pipeline(
                provider_id,
                parser_chain=parser_chain,
            )
        )
        assert payload["record_ids"]
        assert int(payload["search_hits"]) >= 1
        assert bool(payload["retrieved"]) is True
        results.append(payload)

    _ = write_artifact_json(
        "W23A-AT2.5-backend-e2e-matrix.json",
        {
            "parser_chain": parser_chain,
            "results": results,
        },
    )
