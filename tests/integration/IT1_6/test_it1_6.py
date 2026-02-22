# index-retriever-mcp-server — IT1.6
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: MCP tool catalogue exposes required tools.

from index_server.mcp_server import build_registry, list_tool_names
from tests.live_runtime import LiveIndexRuntime


def test_mcp_tool_catalogue(live_service: LiveIndexRuntime) -> None:
    assert live_service.backend_health_check(provider_id="chroma") is True
    names = list_tool_names(build_registry())
    for required in ["profiles_list", "ingest_text", "search", "queue_status"]:
        assert required in names
