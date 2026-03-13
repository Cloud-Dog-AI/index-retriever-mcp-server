# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
