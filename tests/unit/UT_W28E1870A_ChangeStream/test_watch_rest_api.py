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

"""W28E-1870-A REST-surface tests for ``/v1/watches*`` (PS-102 §5.5).

Drives the real FastAPI app built by ``build_api_app`` over the in-process
``service`` fixture, proving watch lifecycle + batch retrieval + RBAC/anon on the
API surface (FR-019/005/009). Auth tokens come from the env-UT contract
(``valid-reader-token:reader``, ``valid-writer-token:writer``, ``valid-admin-token:admin``).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService

pytestmark = [pytest.mark.UT, pytest.mark.api]

_WRITER = {"Authorization": "Bearer valid-writer-token"}
_READER = {"Authorization": "Bearer valid-reader-token"}


@pytest.fixture()
def client(service: IndexService) -> TestClient:
    return TestClient(build_api_app(service=service))


@pytest.mark.UT
@pytest.mark.api
@pytest.mark.req("CS-014")
def test_anonymous_watch_access_is_rejected(client: TestClient) -> None:
    assert client.get("/v1/watches").status_code == 401
    assert client.post("/v1/watches", json={"profile": "default"}).status_code == 401


@pytest.mark.req("FR-019")
def test_full_watch_lifecycle_over_rest(client: TestClient) -> None:
    # create (writer)
    r = client.post(
        "/v1/watches",
        json={"profile": "default", "criteria": {"collection": "docs", "action": ["ingested", "created"]}},
        headers=_WRITER,
    )
    assert r.status_code == 200, r.text
    wid = r.json()["watch_id"]
    assert r.json()["status"]["state"] == "live"

    # list (reader may read)
    lst = client.get("/v1/watches?profile=default", headers=_READER)
    assert lst.status_code == 200
    assert any(w["watch_id"] == wid for w in lst.json()["watches"])

    # inject a synthetic event (test-mode, writer)
    te = client.post(
        f"/v1/watches/{wid}/test-event",
        json={"profile": "default", "action": "created", "object_ref": "synthetic-1"},
        headers=_WRITER,
    )
    assert te.status_code == 200, te.text

    # get_batch (reader)
    batch = client.get(f"/v1/watches/{wid}/events?profile=default", headers=_READER)
    assert batch.status_code == 200, batch.text
    body = batch.json()
    assert len(body["events"]) == 1
    assert body["events"][0]["object_ref"] == "synthetic-1"
    cursor = body["next_cursor"]
    assert cursor

    # ack (reader)
    ack = client.post(f"/v1/watches/{wid}/ack", json={"profile": "default", "ack_cursor": cursor}, headers=_READER)
    assert ack.status_code == 200, ack.text
    assert ack.json()["inflight"] == 0

    # pause / resume (writer)
    paused = client.post(f"/v1/watches/{wid}/pause", json={"profile": "default"}, headers=_WRITER)
    assert paused.json()["state"] == "paused"
    resumed = client.post(f"/v1/watches/{wid}/resume", json={"profile": "default"}, headers=_WRITER)
    assert resumed.json()["state"] == "live"

    # status
    st = client.get(f"/v1/watches/{wid}/status?profile=default", headers=_READER)
    assert st.status_code == 200
    assert st.json()["state"] == "live"

    # delete (writer)
    d = client.request("DELETE", f"/v1/watches/{wid}?profile=default", headers=_WRITER)
    assert d.status_code == 200
    assert d.json()["deleted"] is True


@pytest.mark.req("CS-014")
def test_reader_cannot_create_or_delete_watch(client: TestClient) -> None:
    # reader lacks collection.write -> create denied
    r = client.post("/v1/watches", json={"profile": "default"}, headers=_READER)
    assert r.status_code == 403, r.text


@pytest.mark.req("FR-019")
def test_create_with_invalid_criteria_returns_400(client: TestClient) -> None:
    r = client.post(
        "/v1/watches",
        json={"profile": "default", "criteria": {"unknown_field": 1}},
        headers=_WRITER,
    )
    assert r.status_code == 400, r.text


@pytest.mark.req("FR-020")
def test_unknown_watch_returns_404(client: TestClient) -> None:
    r = client.get("/v1/watches/does-not-exist/status?profile=default", headers=_READER)
    assert r.status_code == 404, r.text
