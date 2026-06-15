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

import pytest

from index_server.auth.middleware import AuthMiddleware
from tests.live_runtime import LiveIndexRuntime
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_api_auth_reject(auth: AuthMiddleware, live_service: LiveIndexRuntime) -> None:
    assert live_service.backend_health_check(provider_id="chroma") is True
    with pytest.raises(PermissionError):
        auth.identity_from_headers({})
