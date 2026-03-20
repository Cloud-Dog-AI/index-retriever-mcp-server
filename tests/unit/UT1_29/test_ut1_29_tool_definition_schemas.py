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

from index_tools.tools.definitions import SearchInput, SearchOutput
from index_tools.tools.registry import ToolRegistry, ToolSpec


def test_tool_definition_schemas() -> None:
    registry = ToolRegistry()
    registry.register(ToolSpec(name="search", input_model=SearchInput, output_model=SearchOutput))
    listing = registry.list_tools()
    assert listing[0]["name"] == "search"
    assert "properties" in listing[0]["input_schema"]
