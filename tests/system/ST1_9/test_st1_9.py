# index-retriever-mcp-server — ST1.9
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live delete by metadata filter.

from tests.live_runtime import LiveIndexRuntime


def test_delete_by_filter(live_service: LiveIndexRuntime) -> None:
    live_service.ingest_text(
        "default",
        "st_delete_filter",
        "delete me",
        "api://del/f1",
        actor="system",
        metadata={"tag": "drop"},
    )
    live_service.ingest_text(
        "default",
        "st_delete_filter",
        "keep me",
        "api://del/f2",
        actor="system",
        metadata={"tag": "keep"},
    )
    removed = live_service.delete_by_filter("default", "st_delete_filter", {"tag": "drop"})
    assert removed >= 1
