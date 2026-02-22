# index-retriever-mcp-server — ST1.5
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local reference-style ingest pipeline.

from tests.local_runtime import LocalIndexRuntime


def test_ingest_reference_pipeline(local_service: LocalIndexRuntime) -> None:
    rec = local_service.ingest_text(
        profile="default",
        collection="st_ref",
        text="reference material body",
        source="file://reference/doc.md",
        actor="system",
    )
    assert rec.record_id
    assert local_service.search("default", "st_ref", "reference")
