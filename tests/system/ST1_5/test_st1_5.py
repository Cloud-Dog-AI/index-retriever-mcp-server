# index-retriever-mcp-server — ST1.5
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live reference-style ingest pipeline.

from tests.live_runtime import LiveIndexRuntime


def test_ingest_reference_pipeline(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text(
        profile="default",
        collection="st_ref",
        text="reference material body",
        source="file://reference/doc.md",
        actor="system",
    )
    assert rec.record_id
    assert live_service.search("default", "st_ref", "reference")
