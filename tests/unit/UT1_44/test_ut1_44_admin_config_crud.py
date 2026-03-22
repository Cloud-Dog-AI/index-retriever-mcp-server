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

import pytest

from index_server.mcp_server import execute_tool
from index_tools.tools.registry import build_default_tool_registry
from index_tools.tools.service import IndexService


def test_service_admin_config_crud_and_mcp_parity(service: IndexService) -> None:
    # Covers: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, CFG-06, CFG-08, CFG-09, CFG-10, CFG-11, CFG-12, CFG-13
    service.attach_auth_api_keys({})
    registry = build_default_tool_registry()

    with pytest.raises(PermissionError):
        service.admin_profile_create("cfg_ut", roles={"writer"})

    created_profile = execute_tool(
        service=service,
        tool_name="admin_profile_create",
        arguments={"profile": "cfg_ut", "config": {"backend": "qdrant", "roles": ["reader", "writer", "admin"]}},
        registry=registry,
        identity_roles={"admin"},
    )
    assert created_profile["profile"]["backend"] == "qdrant"
    assert "cfg_ut" in service.profiles_list()

    updated_profile = execute_tool(
        service=service,
        tool_name="admin_profile_update",
        arguments={"profile": "cfg_ut", "config": {"enabled": False}},
        registry=registry,
        identity_roles={"admin"},
    )
    assert updated_profile["status"] == "ok"
    assert service.profile_get("cfg_ut")["enabled"] is False

    created_user = execute_tool(
        service=service,
        tool_name="admin_user_create",
        arguments={"user_id": "cfg-user", "display_name": "Config User", "roles": ["reader"], "groups": ["ops"]},
        registry=registry,
        identity_roles={"admin"},
    )
    assert created_user["user"]["user_id"] == "cfg-user"

    created_group = execute_tool(
        service=service,
        tool_name="admin_group_create",
        arguments={"group_id": "ops", "roles": ["reader", "writer"], "members": ["cfg-user"]},
        registry=registry,
        identity_roles={"admin"},
    )
    assert created_group["group"]["group_id"] == "ops"

    api_key = execute_tool(
        service=service,
        tool_name="admin_api_key_create",
        arguments={"key_id": "cfg-key", "label": "Config Key", "roles": ["admin", "writer", "reader"]},
        registry=registry,
        identity_roles={"admin"},
    )["api_key"]
    assert api_key["token"].startswith("cd_")
    assert service.api_keys_list()[0]["key_id"] == "cfg-key"
    assert api_key["token"] in service._auth_api_keys

    events = execute_tool(
        service=service,
        tool_name="a2a_config_events",
        arguments={},
        registry=registry,
        identity_roles={"reader"},
    )["events"]
    assert any(item["entity_type"] == "profile" for item in events)
    assert any(item["entity_type"] == "user" for item in events)
    assert any(item["entity_type"] == "group" for item in events)
    assert any(item["entity_type"] == "api_key" for item in events)

    revoked = execute_tool(
        service=service,
        tool_name="admin_api_key_revoke",
        arguments={"key_id": "cfg-key"},
        registry=registry,
        identity_roles={"admin"},
    )["api_key"]
    assert revoked["revoked"] is True
    assert api_key["token"] not in service._auth_api_keys

    execute_tool(
        service=service,
        tool_name="admin_group_delete",
        arguments={"group_id": "ops"},
        registry=registry,
        identity_roles={"admin"},
    )
    execute_tool(
        service=service,
        tool_name="admin_user_delete",
        arguments={"user_id": "cfg-user"},
        registry=registry,
        identity_roles={"admin"},
    )
    execute_tool(
        service=service,
        tool_name="admin_profile_delete",
        arguments={"profile": "cfg_ut"},
        registry=registry,
        identity_roles={"admin"},
    )
    assert "cfg_ut" not in service.profiles_list()
