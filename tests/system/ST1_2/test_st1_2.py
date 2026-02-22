# index-retriever-mcp-server — ST1.2
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local collection create and delete on Chroma backend.

from tests.local_runtime import LocalIndexRuntime


def test_collection_create_delete(local_service: LocalIndexRuntime) -> None:
    name = local_service.ensure_collection("default", "st_collection")
    assert "_default_st_collection" in name
    local_service.cleanup()
