# index-retriever-mcp-server — IT2.5
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Real Weaviate CRUD contract test via cloud_dog_vdb runtime client.

from __future__ import annotations

import asyncio

import pytest

from tests.w23a_helpers import backend_available, backend_skip_reason, run_backend_contract

pytestmark = pytest.mark.skipif(
    not backend_available("weaviate"),
    reason=backend_skip_reason("weaviate") or "weaviate backend unavailable",
)


def test_it2_5_weaviate_contract_roundtrip() -> None:
    result = asyncio.run(run_backend_contract("weaviate"))
    assert result["results"] >= 1
    assert result["deleted"] is True
    assert result["count_after"] == 0
