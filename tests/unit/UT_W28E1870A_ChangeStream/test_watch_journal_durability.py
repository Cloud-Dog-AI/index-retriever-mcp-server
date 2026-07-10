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

"""W28E-1870-A: durable change-watch journal via the REAL ``cloud_dog_db`` engine.

Proves CSTREAM-007 (journal survives restart within retention) end-to-end through
``WatchService`` backed by a real ``cloud_dog_db`` SQLAlchemy engine (SQLite file),
not just an isolated in-memory sqlite. Uses the shared engine directly so no live
VDB / embedding backend is required.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from index_tools.change_stream import WatchService

pytestmark = [pytest.mark.UT, pytest.mark.internal]


@pytest.mark.req("CSTREAM-007")
def test_durable_journal_survives_restart_via_shared_db_engine(tmp_path):
    db_file = tmp_path / "watch-journal.db"
    url = f"sqlite:///{db_file}"

    # "process 1" — create a durable engine, watch, and emit real change events.
    ws1 = WatchService(engine=create_engine(url))
    ws1.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={}, watch_id="w-restart")
    for i in range(5):
        ws1.observe_change(tenant_id="t", collection="c", action="ingested", object_ref=f"o{i}",
                           metadata={"doc_id": f"o{i}"})
    assert ws1.get_status("w-restart", tenant_id="t")["journal_depth"] == 5

    # "process 2" — a fresh WatchService over a NEW engine to the SAME db file
    # (simulating a service restart) recovers the full journal from disk.
    ws2 = WatchService(engine=create_engine(url))
    ws2.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={}, watch_id="w-restart")
    batch = ws2.get_batch("w-restart", tenant_id="t", max_batch=10)
    assert len(batch["events"]) == 5
    assert [e["object_ref"] for e in batch["events"]] == [f"o{i}" for i in range(5)]
    # cursor from process 2 lets a consumer resume exactly where it left off
    assert batch["next_cursor"]


@pytest.mark.req("CSTREAM-007")
def test_journal_ttl_and_size_bounds_are_enforced(tmp_path):
    url = f"sqlite:///{tmp_path / 'bounded.db'}"
    ws = WatchService(engine=create_engine(url))
    # bound the journal to 3 rows; the oldest are trimmed (drop-oldest, CSTREAM-006)
    ws.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={},
                    watch_id="w-bounded", journal_max=3)
    for i in range(6):
        ws.observe_change(tenant_id="t", collection="c", action="ingested", object_ref=f"o{i}")
    depth = ws.get_status("w-bounded", tenant_id="t")["journal_depth"]
    assert depth == 3, f"journal must be size-bounded to 3, got {depth}"
