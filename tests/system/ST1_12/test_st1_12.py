# index-retriever-mcp-server — ST1.12
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local backend and embedding health checks.

from tests.local_runtime import LocalIndexRuntime


def test_audit_log_persistence(local_service: LocalIndexRuntime) -> None:
    assert local_service.backend_health_check(provider_id="chroma") is True
    assert local_service.embedding_health_check() is True
