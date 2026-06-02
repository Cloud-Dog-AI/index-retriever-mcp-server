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

from index_server.auth.middleware import AuthMiddleware
from tests.live_runtime import LiveIndexRuntime


def test_api_auth_accept(auth: AuthMiddleware, live_service: LiveIndexRuntime) -> None:
    assert live_service.backend_health_check(provider_id="chroma") is True
    who = auth.identity_from_headers({"authorization": "Bearer valid-admin-token"})
    assert "admin" in who.roles
