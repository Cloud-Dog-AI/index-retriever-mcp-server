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

from __future__ import annotations

from index_tools.tools.service import IndexService


def test_ut1_48_users_list_empty_state(service: IndexService) -> None:
    """W28A-161C FIX-16: empty user store returns empty list."""
    # Covers: W28A-159-FIX-16 / CC-12
    result = service.users_list()
    assert result == []


def test_ut1_48_users_list_after_create(service: IndexService) -> None:
    """W28A-161C FIX-16: user store returns created user."""
    service.admin_user_create(
        user_id="first-admin",
        roles={"admin"},
        payload={"display_name": "First Admin", "roles": ["admin"]},
        actor="bootstrap",
    )
    result = service.users_list()
    assert len(result) == 1
    assert result[0]["user_id"] == "first-admin"
    assert "admin" in result[0]["roles"]
