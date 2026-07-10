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

"""W28E-1870-A: REAL ingest/delete/collection change-event proof (CSTREAM-012).

These tests exercise the actual ``IndexService`` mutation paths (not a synthetic
test-event) and assert the change lands in a matching watch's journal — the "real
stream/event proof" PS-102 CSTREAM-012 requires to close implementation, as
distinct from health-only proof.
"""

from __future__ import annotations

import time

import pytest

from index_tools.tools.service import IndexService

pytestmark = [pytest.mark.UT, pytest.mark.internal]

_ADMIN = {"admin"}


def _drain_batch(service: IndexService, wid: str, tenant: str, tries: int = 20):
    """Poll the watch journal until an event appears (ingest runs on a worker)."""
    for _ in range(tries):
        batch = service.watch_service.get_batch(wid, tenant_id=tenant)
        if batch["events"]:
            return batch
        # ack the empty in-flight slot? empty batch does not consume a slot.
        time.sleep(0.1)
    return service.watch_service.get_batch(wid, tenant_id=tenant)


@pytest.mark.req("CSTREAM-IR-001")
def test_real_ingest_emits_ingested_change_event(service: IndexService) -> None:
    profile = "default"
    collection = "cw_ingest"
    service.admin_collection_create(profile=profile, collection=collection, roles=_ADMIN)
    wid = service.watch_service.create_watch(
        profile_id=profile, tenant_id=profile, actor="tester",
        criteria={"collection": collection, "action": ["ingested"]},
    )["watch_id"]

    job_id = service.ingest_text(
        profile=profile,
        collection=collection,
        text="the quick brown fox change-watch payload",
        source="file://cw/ingest.txt",
        actor="tester",
    )
    assert job_id

    batch = _drain_batch(service, wid, profile)
    assert batch["events"], "expected a real ingested change event in the watch journal"
    ev = batch["events"][0]
    assert ev["action"] == "ingested"
    assert ev["service_id"] == "index-retriever"
    assert ev["metadata"]["collection"] == collection
    assert ev["metadata"]["source_uri"].endswith("cw/ingest.txt")
    assert ev["criteria_match"]["collection"] == collection


@pytest.mark.req("CSTREAM-IR-001")
def test_real_collection_create_and_delete_emit_change_events(service: IndexService) -> None:
    profile = "default"
    collection = "cw_collection"
    wid = service.watch_service.create_watch(
        profile_id=profile, tenant_id=profile, actor="tester",
        criteria={"action": ["collection_changed"]},
    )["watch_id"]

    service.admin_collection_create(profile=profile, collection=collection, roles=_ADMIN)
    service.admin_collection_delete(profile=profile, collection=collection, roles=_ADMIN)

    batch = service.watch_service.get_batch(wid, tenant_id=profile, max_batch=10)
    actions = [e["action"] for e in batch["events"]]
    versions = [e["object_version"] for e in batch["events"]]
    assert actions.count("collection_changed") == 2
    assert "created" in versions and "deleted" in versions


@pytest.mark.req("CSTREAM-IR-002")
def test_criteria_scoping_excludes_nonmatching_collection(service: IndexService) -> None:
    profile = "default"
    watched = "cw_only"
    other = "cw_other"
    service.admin_collection_create(profile=profile, collection=watched, roles=_ADMIN)
    service.admin_collection_create(profile=profile, collection=other, roles=_ADMIN)
    wid = service.watch_service.create_watch(
        profile_id=profile, tenant_id=profile, actor="tester",
        criteria={"collection": watched, "action": ["ingested"]},
    )["watch_id"]

    service.ingest_text(profile=profile, collection=other, text="ignore me",
                        source="file://cw/other.txt", actor="tester")
    # give the non-matching ingest time to complete
    time.sleep(0.5)
    batch = service.watch_service.get_batch(wid, tenant_id=profile)
    assert batch["events"] == [], "non-matching collection must not appear in the watch"
