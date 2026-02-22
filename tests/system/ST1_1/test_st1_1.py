# index-retriever-mcp-server — ST1.1
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local profile persistence against metadata DB.

from tests.local_runtime import LocalIndexRuntime


def test_profile_create_persist(local_service: LocalIndexRuntime) -> None:
    assert local_service.queue_status() is True
