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

# index-retriever-mcp-server — IT2.1
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Real Chroma CRUD contract test via cloud_dog_vdb runtime client.

from __future__ import annotations

import asyncio

import pytest

from tests.w23a_helpers import backend_available, backend_skip_reason, run_backend_contract

pytestmark = pytest.mark.skipif(
    not backend_available("chroma"),
    reason=backend_skip_reason("chroma") or "chroma backend unavailable",
)


def test_it2_1_chroma_contract_roundtrip() -> None:
    result = asyncio.run(run_backend_contract("chroma"))
    assert result["results"] >= 1
    assert result["deleted"] is True
    assert result["count_after"] == 0
