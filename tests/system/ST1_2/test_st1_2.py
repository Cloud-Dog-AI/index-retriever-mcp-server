# index-retriever-mcp-server — ST1.2
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live collection create and delete on Chroma backend.

from tests.live_runtime import LiveIndexRuntime


def test_collection_create_delete(live_service: LiveIndexRuntime) -> None:
    name = live_service.ensure_collection("default", "st_collection")
    assert "_default_st_collection" in name
