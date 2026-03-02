# index-retriever-mcp-server — IT1.13
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Source metadata round-trip integrity across ingest to search.

from tests.live_runtime import LiveIndexRuntime


def test_source_metadata_round_trip(live_service: LiveIndexRuntime) -> None:
    source_uri = "file://integration/docs/metadata-check.pdf"
    _ = live_service.ingest_text(
        profile="default",
        collection="it_meta_roundtrip",
        text="metadata roundtrip token payload",
        source=source_uri,
        actor="integration",
        provider_id="chroma",
        metadata={"document_id": "IT1-13-DOC"},
    )
    rows = live_service.search(
        "default",
        "it_meta_roundtrip",
        "roundtrip",
        provider_id="chroma",
        filters={"document_id": "IT1-13-DOC"},
    )
    assert rows
    metadata = rows[0]["metadata"]
    assert metadata.get("source_uri") == source_uri
    assert metadata.get("filename") == "metadata-check.pdf"
    assert metadata.get("mime_type") == "application/pdf"
