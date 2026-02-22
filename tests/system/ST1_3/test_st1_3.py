# index-retriever-mcp-server — ST1.3
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local upload-style ingest pipeline to Chroma.

from tests.local_runtime import LocalIndexRuntime


def test_ingest_upload_pipeline(local_service: LocalIndexRuntime) -> None:
    rec = local_service.ingest_text(
        profile="default",
        collection="st_upload",
        text="uploaded content for live system test",
        source="file://upload/sample.txt",
        actor="system",
    )
    assert local_service.job_get(rec.job_id) is not None
    rows = local_service.search("default", "st_upload", "uploaded")
    assert rows
