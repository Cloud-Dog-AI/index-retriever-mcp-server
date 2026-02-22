# index-retriever-mcp-server — ST1.10
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live retention cleanup workflow.

from datetime import datetime, timedelta, timezone

from tests.live_runtime import LiveIndexRuntime


def test_retention_cleanup(live_service: LiveIndexRuntime) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=120)  # noqa: UP017
    live_service.ingest_text(
        "default",
        "st_retention",
        "old record",
        "api://ret/old",
        actor="system",
        created_at=old,
    )
    live_service.ingest_text("default", "st_retention", "new record", "api://ret/new", actor="system")
    removed = live_service.retention_run("default", "st_retention", older_than_days=90)
    assert removed >= 1
