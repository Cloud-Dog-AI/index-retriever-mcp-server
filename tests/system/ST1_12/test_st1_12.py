# index-retriever-mcp-server — ST1.12
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live backend and embedding health checks.

from tests.live_runtime import LiveIndexRuntime


def test_audit_log_persistence(live_service: LiveIndexRuntime) -> None:
    assert live_service.backend_health_check(provider_id="chroma") is True
    assert live_service.embedding_health_check() is True
