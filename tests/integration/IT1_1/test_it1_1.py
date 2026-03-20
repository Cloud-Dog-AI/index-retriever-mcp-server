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

from index_server.api_server import build_health_payload
from tests.live_runtime import LiveIndexRuntime


def test_api_health_endpoint(live_service: LiveIndexRuntime) -> None:
    payload = build_health_payload(service=live_service)
    assert payload["status"] == "ok"

    assert live_service.backend_health_check(provider_id="chroma") is True
    assert live_service.embedding_health_check() is True
