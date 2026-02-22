# index-retriever-mcp-server — IT1.4
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: RBAC ingest gating on API handlers.

import pytest

from index_server.api_server import handle_ingest_text
from index_server.auth.middleware import AuthMiddleware
from tests.live_runtime import LiveIndexRuntime


def test_api_rbac_ingest_gating(live_service: LiveIndexRuntime, auth: AuthMiddleware) -> None:
    payload = {"profile": "default", "collection": "it_rbac_ingest", "text": "secure", "source": "api://it4"}
    with pytest.raises(PermissionError):
        handle_ingest_text(live_service, auth, {"authorization": "Bearer valid-reader-token"}, payload)

    response = handle_ingest_text(live_service, auth, {"authorization": "Bearer valid-writer-token"}, payload)
    assert response["job_id"]
