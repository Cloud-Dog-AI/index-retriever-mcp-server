# index-retriever-mcp-server — IT1.5
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: RBAC admin gating on profile operations.

import pytest

from index_server.admin.endpoints import profile_create
from tests.live_runtime import LiveIndexRuntime


def test_api_rbac_admin_gating(live_service: LiveIndexRuntime) -> None:
    with pytest.raises(PermissionError):
        profile_create(live_service, "it_profile", roles={"writer"})  # type: ignore[arg-type]

    created = profile_create(live_service, "it_profile", roles={"admin"})  # type: ignore[arg-type]
    assert created["status"] == "created"
