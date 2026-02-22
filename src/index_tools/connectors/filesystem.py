# index-retriever-mcp-server — Filesystem Connector
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Filesystem connector with strict scope validation.

from __future__ import annotations

from pathlib import Path

from index_tools.connectors.models import FetchPlan
from index_tools.security.scope import resolve_scoped_path


def resolve(allowed_roots: list[str], requested_path: str) -> FetchPlan:
    path = resolve_scoped_path(allowed_roots=allowed_roots, requested_path=requested_path)
    return FetchPlan(source_type="filesystem", location=str(path), metadata={"scheme": "file"})


def fetch(plan: FetchPlan) -> bytes:
    return Path(plan.location).read_bytes()
