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

from tests.live_runtime import LiveIndexRuntime
import pytest
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")


def test_backend_contract_parity(live_service: LiveIndexRuntime) -> None:
    _ = live_service.ingest_text(
        profile="default",
        collection="ct_parity_chroma",
        text="parity data token",
        source="api://contract/parity/chroma",
        actor="contract",
        provider_id="chroma",
    )
    _ = live_service.ingest_text(
        profile="default",
        collection="ct_parity_qdrant",
        text="parity data token",
        source="api://contract/parity/qdrant",
        actor="contract",
        provider_id="qdrant",
    )

    chroma_rows = live_service.search("default", "ct_parity_chroma", "parity", provider_id="chroma", top_k=3)
    qdrant_rows = live_service.search("default", "ct_parity_qdrant", "parity", provider_id="qdrant", top_k=3)

    assert chroma_rows
    assert qdrant_rows
    assert isinstance(chroma_rows[0].get("metadata"), dict)
    assert isinstance(qdrant_rows[0].get("metadata"), dict)
