# index-retriever-mcp-server — ST1.5
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live reference-style ingest pipeline.

from pathlib import Path

from tests.live_runtime import LiveIndexRuntime


def test_ingest_reference_pipeline(live_service: LiveIndexRuntime, tmp_path: Path) -> None:
    path = tmp_path / "reference-doc.txt"
    path.write_text("reference material body", encoding="utf-8")
    rec = live_service.ingest_reference(
        profile="default",
        collection="st_ref",
        path=str(path),
        actor="system",
    )
    rows = live_service.search("default", "st_ref", "reference")
    assert rows
    assert rows[0]["id"] == rec.record_id
