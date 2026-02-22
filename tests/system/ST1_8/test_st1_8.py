# index-retriever-mcp-server — ST1.8
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local delete by record ID.

from tests.local_runtime import LocalIndexRuntime


def test_delete_by_id(local_service: LocalIndexRuntime) -> None:
    rec = local_service.ingest_text("default", "st_delete_id", "delete target", "api://del/id", actor="system")
    assert local_service.delete_by_id("default", "st_delete_id", rec.record_id)
