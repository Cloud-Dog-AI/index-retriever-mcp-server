# index-retriever-mcp-server — ST1.4
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local text ingest pipeline to Chroma.

from tests.local_runtime import LocalIndexRuntime


def test_ingest_text_pipeline(local_service: LocalIndexRuntime) -> None:
    rec = local_service.ingest_text("default", "st_text", "alpha beta gamma", "api://inline", actor="system")
    found = local_service.retrieve("default", "st_text", rec.record_id)
    assert found is not None
