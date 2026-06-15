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

from __future__ import annotations

from pathlib import Path

from index_server.auth.middleware import AuthMiddleware
from index_tools.audit.logger import AuditLogger
from index_tools.embeddings.adapter import EmbeddingAdapter
from index_tools.queue.engine import QueueEngine
from tests.live_runtime import LiveIndexRuntime
import pytest


def _assert_no_fallback_backends(live_service: LiveIndexRuntime, tmp_path: Path) -> None:
    auth = AuthMiddleware()
    assert auth.backend_name() != "fallback"

    queue = QueueEngine(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'st1_13_jobs.db'}",
        server_id="st1-13",
    )
    assert queue.backend_name() != "fallback"

    audit = AuditLogger(path=tmp_path / "audit-backend-identity.jsonl")
    assert audit.get_backend_name() != "jsonl-fallback"

    embedder = EmbeddingAdapter(
        provider=live_service.embedding_provider,
        model=live_service.embedding_model,
    )
    vectors = embedder.embed(["backend-identity-check"])
    assert vectors and vectors[0]

    required = live_service.required_live_providers()
    assert required
    for provider in required:
        assert provider not in {"fallback", "in-memory"}
        assert live_service.backend_health_check(provider_id=provider) is True
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.req("FR-005")


def test_no_fallback_backend_identity_st(live_service: LiveIndexRuntime, tmp_path: Path) -> None:
    _assert_no_fallback_backends(live_service, tmp_path)
