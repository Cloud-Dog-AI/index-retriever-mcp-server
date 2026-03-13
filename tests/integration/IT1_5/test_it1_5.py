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
