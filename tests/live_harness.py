# index-retriever-mcp-server — Test Harness
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Shared fixtures for system, integration, application, and security tests.

from __future__ import annotations

from pathlib import Path

import pytest

from index_server.auth.middleware import AuthMiddleware
from index_tools.tools.service import IndexService


@pytest.fixture()
def service(tmp_path: Path) -> IndexService:
    audit_path = tmp_path / "audit.jsonl"
    return IndexService(audit_path=str(audit_path))


@pytest.fixture()
def auth() -> AuthMiddleware:
    return AuthMiddleware(api_keys={"test-api-key": {"admin", "maintainer", "writer", "reader"}})
