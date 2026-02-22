# index-retriever-mcp-server — UT1.29
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests tool schema registration and serialisation.

from index_tools.tools.definitions import SearchInput, SearchOutput
from index_tools.tools.registry import ToolRegistry, ToolSpec


def test_tool_definition_schemas() -> None:
    registry = ToolRegistry()
    registry.register(ToolSpec(name="search", input_model=SearchInput, output_model=SearchOutput))
    listing = registry.list_tools()
    assert listing[0]["name"] == "search"
    assert "properties" in listing[0]["input_schema"]
