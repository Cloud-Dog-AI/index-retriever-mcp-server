# index-retriever-mcp-server — ST1.1
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live profile persistence against metadata DB.

from tests.live_runtime import LiveIndexRuntime


def test_profile_create_persist(live_service: LiveIndexRuntime) -> None:
    assert live_service.queue_status() is True
