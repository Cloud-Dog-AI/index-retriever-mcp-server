# index-retriever-mcp-server — IT1.2
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Auth middleware rejects unauthenticated requests.

import pytest

from index_server.auth.middleware import AuthMiddleware
from tests.live_runtime import LiveIndexRuntime


def test_api_auth_reject(auth: AuthMiddleware, live_service: LiveIndexRuntime) -> None:
    assert live_service.backend_health_check(provider_id="chroma") is True
    with pytest.raises(PermissionError):
        auth.authenticate({})
