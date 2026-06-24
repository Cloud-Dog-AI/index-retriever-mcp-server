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

from index_tools.tools.registry import build_default_tool_registry
import pytest
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-016") # W28E-1805A semantic binding


def test_ut_40_tool_registry_contract_fields() -> None:
    # Covers: FR-P002, FR-016
    registry = build_default_tool_registry()
    tools = registry.list_tools()
    assert tools
    # 95 = 90 (W28E-603 baseline) + 2 shared IDAM admin tools landed by W28A-876
    # + hdro_extract + W28M-1603D structure_template_delete
    # + W28E-1805B structure_template_match. Source is canonical.
    assert len(tools) == 95

    names = [str(tool["name"]) for tool in tools]
    assert len(names) == len(set(names))
    assert names[0] == "profiles_list"
    assert "ingest_health" in names
    # W28E-603 document-structure family (Phase 1)
    for structure_tool in (
        "structure_health",
        "structure_document_create",
        "structure_document_get",
        "structure_document_list",
        "structure_document_delete",
        "structure_outline_get",
        "structure_pages_list",
        "structure_sections_list",
    ):
        assert structure_tool in names

    for tool in tools:
        assert isinstance(tool.get("name"), str)
        assert tool["name"]
        assert isinstance(tool.get("description"), str)
        assert tool["description"], f"Tool {tool['name']!r} has blank description"
        assert isinstance(tool.get("handler"), str)
        assert tool["handler"]
