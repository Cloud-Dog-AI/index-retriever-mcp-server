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

# index-retriever-mcp-server — AT1.2
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live idempotent ingest workflow.

from datetime import datetime, timedelta, timezone

from tests.live_runtime import LiveIndexRuntime


def test_full_workflow_deduplicate_skip(live_service: LiveIndexRuntime) -> None:
    key = "at-idempotent-key"
    first = live_service.ingest_text(
        "default",
        "at_dedupe",
        "dedupe text",
        "api://at/dedupe",
        actor="application",
        idempotency_key=key,
        dedupe_policy="skip",
    )
    second = live_service.ingest_text(
        "default",
        "at_dedupe",
        "dedupe text",
        "api://at/dedupe",
        actor="application",
        idempotency_key=key,
        dedupe_policy="skip",
    )
    assert first.job_id == second.job_id
    assert first.record_id == second.record_id
    rows = live_service.search("default", "at_dedupe", "dedupe", top_k=20)
    assert len(rows) == 1


def test_full_workflow_reindex_replace_on_change_or_stale(live_service: LiveIndexRuntime) -> None:
    initial = live_service.ingest_text(
        "default",
        "at_replace",
        "replace token original",
        "api://at/replace",
        actor="application",
        metadata={"document_id": "AT1-2-REPLACE"},
        dedupe_policy="replace",
        indexing_signature="chunk:v1",
    )

    changed = live_service.ingest_text(
        "default",
        "at_replace",
        "replace token changed",
        "api://at/replace",
        actor="application",
        metadata={"document_id": "AT1-2-REPLACE"},
        dedupe_policy="replace",
        indexing_signature="chunk:v1",
    )
    assert changed.record_id != initial.record_id
    superseded_initial = live_service.retrieve("default", "at_replace", initial.record_id)
    assert superseded_initial is not None
    assert str(superseded_initial.lifecycle_state) != "active"

    reindexed = live_service.ingest_text(
        "default",
        "at_replace",
        "replace token changed",
        "api://at/replace",
        actor="application",
        metadata={"document_id": "AT1-2-REPLACE"},
        dedupe_policy="replace",
        indexing_signature="chunk:v2",
    )
    assert reindexed.record_id != changed.record_id
    superseded_changed = live_service.retrieve("default", "at_replace", changed.record_id)
    assert superseded_changed is not None
    assert str(superseded_changed.lifecycle_state) != "active"

    old_created_at = datetime.now(timezone.utc) - timedelta(days=365)  # noqa: UP017
    stale = live_service.ingest_text(
        "default",
        "at_stale_reindex",
        "stale token payload",
        "api://at/stale",
        actor="application",
        metadata={"document_id": "AT1-2-STALE"},
        dedupe_policy="skip",
        stale_after_days=30,
        created_at=old_created_at,
        indexing_signature="chunk:v1",
    )
    refreshed = live_service.ingest_text(
        "default",
        "at_stale_reindex",
        "stale token payload",
        "api://at/stale",
        actor="application",
        metadata={"document_id": "AT1-2-STALE"},
        dedupe_policy="skip",
        stale_after_days=30,
        indexing_signature="chunk:v1",
    )
    assert refreshed.record_id != stale.record_id
    superseded_stale = live_service.retrieve("default", "at_stale_reindex", stale.record_id)
    assert superseded_stale is not None
    assert str(superseded_stale.lifecycle_state) != "active"
