# index-retriever-mcp-server — ST1.4
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live text ingest pipeline to Chroma.

from tests.live_runtime import LiveIndexRuntime


def test_ingest_text_pipeline(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text("default", "st_text", "alpha beta gamma", "api://inline", actor="system")
    found = live_service.retrieve("default", "st_text", rec.record_id)
    assert found is not None
