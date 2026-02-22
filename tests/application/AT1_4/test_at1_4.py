# index-retriever-mcp-server — AT1.4
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live retention policy workflow.

from datetime import datetime, timedelta, timezone

from tests.live_runtime import LiveIndexRuntime


def test_full_workflow_retention_enforcement(live_service: LiveIndexRuntime) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=365)  # noqa: UP017
    _ = live_service.ingest_text(
        "default",
        "at_retention",
        "old payload",
        "api://at/old",
        actor="application",
        created_at=old,
    )
    _ = live_service.ingest_text("default", "at_retention", "new payload", "api://at/new", actor="application")
    removed = live_service.retention_run("default", "at_retention", older_than_days=90)
    assert removed >= 1
