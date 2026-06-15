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

from index_tools.audit.events import Actor, AuditEvent, Target
import pytest
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-006")


def test_audit_event_shape() -> None:
    # Covers: FR-06
    event = AuditEvent(
        event_type="tool.call",
        actor=Actor(type="user", id="user-1", roles=["writer"]),
        action="execute",
        outcome="success",
        correlation_id="ut1-7-correlation",
        service="index-retriever-mcp-server",
        service_instance="ut1-7",
        environment="test",
        target=Target(type="collection", id="kb", name="kb"),
        details={"tool": "ingest_text", "profile": "default"},
    )
    payload = event.to_dict()
    assert payload["actor"]["id"] == "user-1"
    assert payload["action"] == "execute"
    assert payload["correlation_id"] == "ut1-7-correlation"
    assert payload["timestamp"] is not None
