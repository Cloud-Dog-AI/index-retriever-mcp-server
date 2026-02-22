# index-retriever-mcp-server — IT1.7
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: MCP tool execution over live runtime.

from index_server.mcp_server import execute_tool
from tests.live_runtime import LiveIndexRuntime


def test_mcp_tool_execution(live_service: LiveIndexRuntime) -> None:
    _ = execute_tool(
        live_service,
        "ingest_text",
        {
            "profile": "default",
            "collection": "it_mcp",
            "text": "integration mcp searchable",
            "source": "api://it7",
            "actor": "integration",
        },
    )
    out = execute_tool(
        live_service,
        "search",
        {"profile": "default", "collection": "it_mcp", "query": "searchable", "top_k": 3},
    )
    assert out["results"]
