# index-retriever-mcp-server — IT2.6
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Real Infinity CRUD contract test via cloud_dog_vdb runtime client.

from __future__ import annotations

import asyncio

import pytest

from tests.w23a_helpers import backend_available, backend_skip_reason, run_backend_contract

pytestmark = pytest.mark.skipif(
    not backend_available("infinity"),
    reason=backend_skip_reason("infinity") or "infinity backend unavailable",
)


def test_it2_6_infinity_contract_roundtrip() -> None:
    result = asyncio.run(run_backend_contract("infinity"))
    assert result["results"] >= 1
    assert result["deleted"] is True
    assert result["count_after"] == 0
