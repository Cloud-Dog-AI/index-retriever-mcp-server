# index-retriever-mcp-server — ST1.7
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live metadata filter behaviour.

from tests.live_runtime import LiveIndexRuntime


def test_search_metadata_filter(live_service: LiveIndexRuntime) -> None:
    live_service.ingest_text(
        "default",
        "st_filter",
        "tenant alpha entry",
        "api://alpha",
        actor="system",
        provider_id="qdrant",
        metadata={"tenant": "alpha"},
    )
    live_service.ingest_text(
        "default",
        "st_filter",
        "tenant beta entry",
        "api://beta",
        actor="system",
        provider_id="qdrant",
        metadata={"tenant": "beta"},
    )
    rows = live_service.search("default", "st_filter", "entry", provider_id="qdrant", filters={"tenant": "alpha"})
    assert rows
    assert all(r["metadata"].get("tenant") == "alpha" for r in rows)
