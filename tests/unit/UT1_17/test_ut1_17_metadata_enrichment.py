# index-retriever-mcp-server — UT1.17
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests metadata enrichment output fields.

from index_tools.pipeline.metadata import build_metadata


def test_metadata_enrichment() -> None:
    data = build_metadata("data/doc.txt", b"hello", profile="default", collection="kb")
    assert data["source"] == "data/doc.txt"
    assert data["size"] == 5
    assert data["profile"] == "default"
    assert data["collection"] == "kb"
    assert "content_hash" in data
