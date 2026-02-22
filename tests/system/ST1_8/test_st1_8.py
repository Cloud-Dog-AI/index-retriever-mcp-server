# index-retriever-mcp-server — ST1.8
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live delete by record ID.

from tests.live_runtime import LiveIndexRuntime


def test_delete_by_id(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text("default", "st_delete_id", "delete target", "api://del/id", actor="system")
    assert live_service.delete_by_id("default", "st_delete_id", rec.record_id)
