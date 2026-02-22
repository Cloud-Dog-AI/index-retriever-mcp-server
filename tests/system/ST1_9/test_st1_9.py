# index-retriever-mcp-server — ST1.9
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local delete by metadata filter.

from tests.local_runtime import LocalIndexRuntime


def test_delete_by_filter(local_service: LocalIndexRuntime) -> None:
    local_service.ingest_text(
        "default",
        "st_delete_filter",
        "delete me",
        "api://del/f1",
        actor="system",
        metadata={"tag": "drop"},
    )
    local_service.ingest_text(
        "default",
        "st_delete_filter",
        "keep me",
        "api://del/f2",
        actor="system",
        metadata={"tag": "keep"},
    )
    removed = local_service.delete_by_filter("default", "st_delete_filter", {"tag": "drop"})
    assert removed >= 1
