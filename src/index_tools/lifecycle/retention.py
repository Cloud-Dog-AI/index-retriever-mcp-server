# index-retriever-mcp-server — Retention Policies
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Retention policy checks for lifecycle management.

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def older_than_days(created_at: datetime, days: int) -> bool:
    """Return True if a document is older than the configured threshold."""
    threshold = datetime.now(timezone.utc) - timedelta(days=days)  # noqa: UP017
    return created_at < threshold
