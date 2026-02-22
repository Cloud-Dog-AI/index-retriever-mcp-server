# index-retriever-mcp-server — ST1.3
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live upload-style ingest pipeline to Chroma.

from tests.live_runtime import LiveIndexRuntime


def test_ingest_upload_pipeline(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text(
        profile="default",
        collection="st_upload",
        text="uploaded content for live system test",
        source="file://upload/sample.txt",
        actor="system",
    )
    assert live_service.job_get(rec.job_id) is not None
    rows = live_service.search("default", "st_upload", "uploaded")
    assert rows
