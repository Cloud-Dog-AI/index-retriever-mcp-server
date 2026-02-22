# index-retriever-mcp-server — AT1.1
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live end-to-end ingest, search, and retrieve workflow.

from tests.live_runtime import LiveIndexRuntime


def test_full_workflow_upload_search_retrieve(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text(
        profile="default",
        collection="at_upload",
        text="application workflow payload",
        source="file://application/workflow.txt",
        actor="application",
    )
    rows = live_service.search("default", "at_upload", "workflow")
    assert rows
    record = live_service.retrieve("default", "at_upload", rec.record_id)
    assert record is not None
    assert "payload" in record.content
