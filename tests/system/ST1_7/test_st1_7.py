# index-retriever-mcp-server — ST1.7
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local metadata filter behaviour.

from tests.local_runtime import LocalIndexRuntime


def test_search_metadata_filter(local_service: LocalIndexRuntime) -> None:
    local_service.ingest_text(
        "default",
        "st_filter",
        "tenant alpha entry",
        "api://alpha",
        actor="system",
        provider_id="qdrant",
        metadata={"tenant": "alpha"},
    )
    local_service.ingest_text(
        "default",
        "st_filter",
        "tenant beta entry",
        "api://beta",
        actor="system",
        provider_id="qdrant",
        metadata={"tenant": "beta"},
    )
    rows = local_service.search("default", "st_filter", "entry", provider_id="qdrant", filters={"tenant": "alpha"})
    assert rows
    assert all(r["metadata"].get("tenant") == "alpha" for r in rows)
