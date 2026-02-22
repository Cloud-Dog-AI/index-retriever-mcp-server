# index-retriever-mcp-server — ST1.10
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local retention cleanup workflow.

from datetime import datetime, timedelta, timezone

from tests.local_runtime import LocalIndexRuntime


def test_retention_cleanup(local_service: LocalIndexRuntime) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=120)  # noqa: UP017
    local_service.ingest_text(
        "default",
        "st_retention",
        "old record",
        "api://ret/old",
        actor="system",
        created_at=old,
    )
    local_service.ingest_text("default", "st_retention", "new record", "api://ret/new", actor="system")
    removed = local_service.retention_run("default", "st_retention", older_than_days=90)
    assert removed >= 1
