# index-retriever-mcp-server — IT1.1
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live health payload includes backend and embedding checks.

from index_server.api_server import build_health_payload
from tests.live_runtime import LiveIndexRuntime


def test_api_health_endpoint(live_service: LiveIndexRuntime) -> None:
    payload = build_health_payload(service=live_service)
    assert payload["status"] == "ok"

    assert live_service.backend_health_check(provider_id="chroma") is True
    assert live_service.embedding_health_check() is True
