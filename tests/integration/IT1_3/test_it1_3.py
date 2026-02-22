# index-retriever-mcp-server — IT1.3
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Auth middleware accepts valid credentials.

from index_server.auth.middleware import AuthMiddleware
from tests.live_runtime import LiveIndexRuntime


def test_api_auth_accept(auth: AuthMiddleware, live_service: LiveIndexRuntime) -> None:
    assert live_service.backend_health_check(provider_id="chroma") is True
    who = auth.authenticate({"authorization": "Bearer valid-admin-token"})
    assert "admin" in who.roles
