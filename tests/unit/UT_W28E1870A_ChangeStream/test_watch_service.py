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

"""W28E-1870-A unit tests for the ``WatchService`` VDB change-watch adapter.

Covers FR-019/002 (VDB watch + criteria), FR-020 (cursor/ack/recover),
FR-020 (backpressure), FR-020 (durable journal), CS-014 (tenancy),
FR-002 (audit rows), and NF-002 (redaction) at the adapter layer.
"""

from __future__ import annotations

import pytest
from cloud_dog_api_kit.change_stream.errors import (
    InvalidCriteria,
    RateLimited,
    WatchNotFound,
)
from sqlalchemy import create_engine

from index_tools.change_stream import WatchService, make_audit_sink

pytestmark = [pytest.mark.UT, pytest.mark.internal]


class _CaptureAudit:
    def __init__(self):
        self.rows = []

    def log_admin_action(self, **kw):
        self.rows.append((kw.get("action"), kw.get("target_id"), kw.get("new_value")))


def _svc(engine=None, audit=None):
    sink = make_audit_sink(audit) if audit is not None else None
    return WatchService(engine=engine, audit_sink=sink)


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-019")
def test_create_list_status_pause_resume_delete_lifecycle():
    ws = _svc()
    w = ws.create_watch(profile_id="p", tenant_id="t", actor="alice", criteria={"collection": "docs"})
    wid = w["watch_id"]
    assert w["status"]["state"] == "live"
    assert [x["watch_id"] for x in ws.list_watches(tenant_id="t")] == [wid]
    assert ws.pause(wid, tenant_id="t")["state"] == "paused"
    assert ws.resume(wid, tenant_id="t")["state"] == "live"
    assert ws.delete(wid, tenant_id="t")["deleted"] is True
    assert ws.list_watches(tenant_id="t") == []


@pytest.mark.req("FR-019")
def test_observe_change_emits_only_to_matching_live_watches():
    ws = _svc()
    match_w = ws.create_watch(profile_id="p", tenant_id="t", actor="a",
                              criteria={"collection": "docs", "action": ["ingested"]})["watch_id"]
    other_w = ws.create_watch(profile_id="p", tenant_id="t", actor="a",
                              criteria={"collection": "other"})["watch_id"]
    hit = ws.observe_change(tenant_id="t", collection="docs", action="ingested", object_ref="d1",
                            source_uri="https://x/a", metadata={"doc_id": "d1"})
    assert hit == [match_w]
    assert other_w not in hit
    # batch only shows in the matching watch
    assert len(ws.get_batch(match_w, tenant_id="t")["events"]) == 1
    assert len(ws.get_batch(other_w, tenant_id="t")["events"]) == 0


@pytest.mark.req("FR-019")
def test_paused_watch_does_not_receive_events():
    ws = _svc()
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={})["watch_id"]
    ws.pause(wid, tenant_id="t")
    emitted = ws.observe_change(tenant_id="t", collection="docs", action="ingested", object_ref="d1")
    assert emitted == []
    assert ws.get_status(wid, tenant_id="t")["journal_depth"] == 0


@pytest.mark.req("CS-014")
def test_cross_tenant_isolation_is_hard_failure():
    ws = _svc()
    wid = ws.create_watch(profile_id="p", tenant_id="tenant-a", actor="a", criteria={})["watch_id"]
    # tenant-b cannot see tenant-a's watch (not-found, no existence leak)
    with pytest.raises(WatchNotFound):
        ws.get_status(wid, tenant_id="tenant-b")
    with pytest.raises(WatchNotFound):
        ws.get_batch(wid, tenant_id="tenant-b")
    # tenant-b's observed change never lands in tenant-a's journal
    ws.observe_change(tenant_id="tenant-b", collection="docs", action="ingested", object_ref="d1")
    assert ws.get_status(wid, tenant_id="tenant-a")["journal_depth"] == 0
    assert ws.list_watches(tenant_id="tenant-b") == []


@pytest.mark.req("FR-020")
def test_cursor_batch_ack_recover_flow():
    ws = _svc()
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={}, max_batch=2)["watch_id"]
    for i in range(3):
        ws.observe_change(tenant_id="t", collection="c", action="ingested", object_ref=f"o{i}")
    b1 = ws.get_batch(wid, tenant_id="t")
    assert len(b1["events"]) == 2
    ws.ack(wid, tenant_id="t", ack_cursor=b1["next_cursor"])
    b2 = ws.get_batch(wid, tenant_id="t", since_cursor=b1["next_cursor"])
    assert len(b2["events"]) == 1
    resume = ws.recover(wid, tenant_id="t")
    assert resume["resume_cursor"]


@pytest.mark.req("FR-020")
def test_backpressure_throttles_unacked_batches():
    ws = _svc()
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a",
                          criteria={}, max_batch=1, max_inflight=1)["watch_id"]
    for i in range(3):
        ws.observe_change(tenant_id="t", collection="c", action="ingested", object_ref=f"o{i}")
    ws.get_batch(wid, tenant_id="t")  # 1 in-flight
    with pytest.raises(RateLimited):
        ws.get_batch(wid, tenant_id="t", since_cursor=None)


@pytest.mark.req("FR-020")
def test_durable_sql_journal_persists_across_service_instances():
    # a shared file-backed sqlite engine simulates restart durability
    import os
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        eng = create_engine(f"sqlite:///{path}")
        ws1 = WatchService(engine=eng)
        ws1.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={}, watch_id="w-durable")
        for i in range(2):
            ws1.observe_change(tenant_id="t", collection="c", action="ingested", object_ref=f"o{i}")
        # a second WatchService over the SAME engine + same watch_id sees the journal
        ws2 = WatchService(engine=create_engine(f"sqlite:///{path}"))
        ws2.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={}, watch_id="w-durable")
        b = ws2.get_batch("w-durable", tenant_id="t")
        assert len(b["events"]) == 2
    finally:
        os.unlink(path)


@pytest.mark.req("FR-002")
def test_audit_rows_emitted_for_lifecycle_and_emission():
    audit = _CaptureAudit()
    ws = _svc(audit=audit)
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={})["watch_id"]
    ws.observe_change(tenant_id="t", collection="c", action="ingested", object_ref="o1")
    ws.get_batch(wid, tenant_id="t")
    actions = {a for a, _, _ in audit.rows}
    assert "change_watch.watch_create" in actions
    assert "change_watch.event_emit" in actions
    assert "change_watch.batch_delivery" in actions


@pytest.mark.req("NF-002")
def test_secret_bearing_metadata_is_redacted_in_batches():
    ws = _svc()
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={})["watch_id"]
    ws.observe_change(tenant_id="t", collection="c", action="ingested", object_ref="o1",
                      metadata={"doc_id": "o1", "api_key": "super-secret", "authorization": "Bearer xyz"})
    b = ws.get_batch(wid, tenant_id="t")
    # the typed envelope metadata never carries the raw secret keys, and any that
    # slip through are redacted by the foundation's to_dict(redact=True)
    dumped = str(b["events"][0])
    assert "super-secret" not in dumped
    assert "Bearer xyz" not in dumped


@pytest.mark.req("FR-019")
def test_test_event_injects_synthetic_without_backend_mutation():
    ws = _svc()
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={})["watch_id"]
    res = ws.test_event(wid, tenant_id="t", action="created", object_ref="synthetic-1")
    assert res["emitted_seq"] >= 1
    b = ws.get_batch(wid, tenant_id="t")
    assert b["events"][0]["object_ref"] == "synthetic-1"
    assert b["events"][0]["action"] == "created"


@pytest.mark.req("FR-019")
def test_create_rejects_invalid_criteria_before_watch_starts():
    ws = _svc()
    with pytest.raises(InvalidCriteria):
        ws.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={"unknown_field": 1})
    # no watch was created
    assert ws.list_watches(tenant_id="t") == []


@pytest.mark.req("NF-002")
def test_envelope_carries_typed_index_metadata_and_criteria_match():
    ws = _svc()
    wid = ws.create_watch(profile_id="prof", tenant_id="t", actor="a",
                          criteria={"collection": "docs"})["watch_id"]
    ws.observe_change(tenant_id="t", collection="docs", action="ingested", object_ref="doc-9",
                      source_uri="https://data.gov/x.pdf", title="X", language="en",
                      doc_id="doc-9", metadata={"embedding_model": "nomic", "lifecycle_state": "active"})
    ev = ws.get_batch(wid, tenant_id="t")["events"][0]
    assert ev["service_id"] == "index-retriever"
    assert ev["source_type"] == "vdb_collection"
    assert ev["metadata"]["collection"] == "docs"
    assert ev["metadata"]["source_domain"] == "data.gov"
    assert ev["metadata"]["embedding_model"] == "nomic"
    assert ev["criteria_match"]["collection"] == "docs"
    assert ev["cursor"]  # stamped opaque cursor
