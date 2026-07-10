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

"""W28E-1870-A change-watch surface tests: MCP tool registry/dispatch + A2A card.

Exercises CSTREAM-001 (surface parity) at the registry + dispatch level without a
live server, and CSTREAM-002 (nonblocking) by proving batch retrieval returns
promptly with an empty batch when no events are pending.
"""

from __future__ import annotations

import time

import pytest

from index_tools.change_stream import WatchService
from index_tools.tools.registry import build_default_tool_registry

pytestmark = [pytest.mark.UT]

_WATCH_TOOLS = {
    "index_watch_create",
    "index_watch_list",
    "index_watch_status",
    "index_watch_get_batch",
    "index_watch_ack",
    "index_watch_recover",
    "index_watch_pause",
    "index_watch_resume",
    "index_watch_delete",
    "index_watch_test_event",
}


@pytest.mark.mcp
@pytest.mark.req("CSTREAM-001")
def test_all_watch_mcp_tools_are_registered():
    reg = build_default_tool_registry()
    names = {t["name"] for t in reg.list_tools()}
    assert _WATCH_TOOLS.issubset(names)


@pytest.mark.mcp
@pytest.mark.req("CSTREAM-009")
def test_watch_tool_permissions_split_read_and_write():
    from index_server.mcp_server import _required_permission_for_tool

    for read_tool in ("index_watch_list", "index_watch_status", "index_watch_get_batch",
                      "index_watch_ack", "index_watch_recover"):
        assert _required_permission_for_tool(read_tool) == "collection.read"
    for write_tool in ("index_watch_create", "index_watch_pause", "index_watch_resume",
                       "index_watch_delete", "index_watch_test_event"):
        assert _required_permission_for_tool(write_tool) == "collection.write"


@pytest.mark.a2a
@pytest.mark.req("CSTREAM-001")
def test_a2a_agent_card_advertises_watch_skills():
    from index_server.a2a_server import AGENT_CARD

    skill_ids = {s["id"] for s in AGENT_CARD["skills"]}
    assert _WATCH_TOOLS.issubset(skill_ids)
    assert AGENT_CARD["capabilities"]["streaming"] is True


@pytest.mark.internal
@pytest.mark.req("CSTREAM-002")
def test_get_batch_is_nonblocking_when_no_events_pending():
    ws = WatchService()
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={})["watch_id"]
    t0 = time.monotonic()
    batch = ws.get_batch(wid, tenant_id="t")
    elapsed = time.monotonic() - t0
    # empty batch + a current cursor returned immediately (no worker held)
    assert batch["events"] == []
    assert batch["next_cursor"]
    assert elapsed < 0.5


@pytest.mark.internal
@pytest.mark.req("CSTREAM-004")
def test_error_model_codes_are_stable():
    from cloud_dog_api_kit.change_stream.errors import ERROR_CODES

    for code in ("invalid_criteria", "unauthorised", "cursor_expired", "rate_limited"):
        assert code in ERROR_CODES
