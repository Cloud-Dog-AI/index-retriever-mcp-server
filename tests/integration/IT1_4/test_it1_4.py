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
