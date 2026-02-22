# index-retriever-mcp-server — IT1.8
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Correlation IDs propagate in health response.

from index_server.api_server import build_health_payload
from tests.live_runtime import LiveIndexRuntime


def test_correlation_id_propagation(live_service: LiveIndexRuntime) -> None:
    payload = build_health_payload(service=live_service, correlation_id="it-corr-1")
    assert payload["correlation_id"] == "it-corr-1"
