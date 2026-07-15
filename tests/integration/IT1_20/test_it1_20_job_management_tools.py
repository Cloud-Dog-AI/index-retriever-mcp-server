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

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService
from tests.http_paths import api_tools_path
import pytest


def _call_tool(client: TestClient, tool_name: str, payload: dict[str, object], token: str) -> dict[str, object]:
    response = client.post(
        api_tools_path(tool_name),
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _post_tool(client: TestClient, tool_name: str, payload: dict[str, object], token: str):
    return client.post(
        api_tools_path(tool_name),
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def _current_user_id(client: TestClient, token: str) -> str:
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    user = response.json().get("user")
    assert isinstance(user, dict)
    return str(user["id"])


def _job_actor(job: dict[str, object]) -> str:
    payload = job.get("payload")
    nested = payload if isinstance(payload, dict) else {}
    for key in ("request_auth_identity", "user_id", "actor"):
        value = job.get(key)
        if value:
            return str(value)
    for key in ("request_auth_identity", "user_id", "actor"):
        value = nested.get(key)
        if value:
            return str(value)
    return ""
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_job_management_tools_contract(service: IndexService) -> None:
    # Covers: FR-07
    client = TestClient(build_api_app(service=service))
    writer_actor = _current_user_id(client, "valid-writer-token")

    _ = _call_tool(
        client,
        "admin_collection_create",
        {"profile": "default", "collection": "it1_20_jobs"},
        "valid-admin-token",
    )

    queued = _call_tool(
        client,
        "ingest_text",
        {
            "profile": "default",
            "collection": "it1_20_jobs",
            "text": "job management baseline payload",
            "source": "file://it1_20/jobs-0.txt",
        },
        "valid-writer-token",
    )
    job_id = str(queued["job_id"])
    assert queued["status"] == "succeeded"

    admin_queued = _call_tool(
        client,
        "ingest_text",
        {
            "profile": "default",
            "collection": "it1_20_jobs",
            "text": "job management admin owned payload",
            "source": "file://it1_20/jobs-admin-owned.txt",
        },
        "valid-admin-token",
    )
    admin_job_id = str(admin_queued["job_id"])

    listed = _call_tool(client, "job_list", {}, "valid-admin-token")
    jobs = listed.get("jobs")
    assert isinstance(jobs, list)
    assert any(str(item.get("job_id", "")) == job_id for item in jobs)
    assert any(str(item.get("job_id", "")) == admin_job_id for item in jobs)

    writer_list = _call_tool(client, "job_list", {"limit": 2000}, "valid-writer-token")
    writer_jobs = writer_list.get("jobs")
    assert isinstance(writer_jobs, list)
    assert all(_job_actor(item) == writer_actor for item in writer_jobs if isinstance(item, dict))
    assert all(str(item.get("job_id", "")) != admin_job_id for item in writer_jobs if isinstance(item, dict))
    assert _post_tool(client, "job_get", {"job_id": admin_job_id}, "valid-writer-token").status_code == 403
    assert _post_tool(client, "job_cancel", {"job_id": admin_job_id}, "valid-writer-token").status_code == 403

    succeeded_only = _call_tool(client, "job_list", {"status": "succeeded"}, "valid-admin-token")
    succeeded_jobs = succeeded_only.get("jobs")
    assert isinstance(succeeded_jobs, list)
    assert any(str(item.get("job_id", "")) == job_id for item in succeeded_jobs)

    # GAP A (W28E-1805B): an inline job created through the API carries the request
    # correlation id into its audit context (non-null on the persisted JobRecord).
    succeeded_record = next(item for item in succeeded_jobs if str(item.get("job_id", "")) == job_id)
    assert succeeded_record.get("correlation_id")

    # GAP B (W28E-1805B): cancelling an already-terminal (succeeded) job is rejected — the
    # record is NOT flipped to cancelled; a clear no-op is returned instead.
    cancelled = _call_tool(client, "job_cancel", {"job_id": job_id}, "valid-admin-token")
    assert cancelled.get("cancelled") is False
    assert "terminal" in str(cancelled.get("reason", "")).lower()
    cancelled_job = cancelled.get("job")
    assert isinstance(cancelled_job, dict)
    assert cancelled_job.get("job_id") == job_id
    assert str(cancelled_job.get("status", "")).lower() == "succeeded"

    # the job remains succeeded after the rejected cancel (terminal-state integrity)
    still_succeeded = _call_tool(client, "job_get", {"job_id": job_id}, "valid-admin-token")
    assert str(still_succeeded.get("job", {}).get("status", "")).lower() == "succeeded"

    deleted = _call_tool(client, "job_delete", {"job_id": job_id}, "valid-admin-token")
    assert deleted.get("job_id") == job_id
    assert deleted.get("deleted") is True
    listed_after_delete = _call_tool(client, "job_list", {}, "valid-admin-token")
    remaining_jobs = listed_after_delete.get("jobs")
    assert isinstance(remaining_jobs, list)
    assert all(str(item.get("job_id", "")) != job_id for item in remaining_jobs)

    original_upsert = service.vdb.upsert_records

    async def _fail_upsert(*args, **kwargs):
        _ = args, kwargs
        raise RuntimeError("forced embed failure for IT1.20 retry path")

    service.vdb.upsert_records = _fail_upsert
    failed_job_id = service.ingest_text(
        profile="default",
        collection="it1_20_jobs",
        text="job management forced failure payload",
        source="file://it1_20/jobs-failed.txt",
        actor="integration",
    )
    failed_job = service.job_wait(failed_job_id)
    service.vdb.upsert_records = original_upsert

    assert failed_job.status.value == "dead_lettered"
    assert failed_job.job_id == failed_job_id

    failed_list = _call_tool(client, "job_list", {"status": "dead_lettered"}, "valid-admin-token")
    failed_jobs = failed_list.get("jobs")
    assert isinstance(failed_jobs, list)
    assert any(str(item.get("job_id", "")) == failed_job_id for item in failed_jobs if isinstance(item, dict))

    retried = _call_tool(client, "job_retry", {"job_id": failed_job_id}, "valid-admin-token")
    retried_job = retried.get("job")
    assert isinstance(retried_job, dict)
    assert retried_job.get("job_id") == failed_job_id
    assert str(retried_job.get("status", "")).lower() in {"queued", "running", "succeeded"}

    service.vdb.upsert_records = _fail_upsert
    writer_failed_job_id = service.ingest_text(
        profile="default",
        collection="it1_20_jobs",
        text="job management writer-owned forced failure payload",
        source="file://it1_20/jobs-writer-failed.txt",
        actor=writer_actor,
    )
    writer_failed_job = service.job_wait(writer_failed_job_id)
    service.vdb.upsert_records = original_upsert
    assert writer_failed_job.status.value == "dead_lettered"

    writer_retry = _call_tool(client, "job_retry", {"job_id": writer_failed_job_id}, "valid-writer-token")
    writer_retry_job = writer_retry.get("job")
    assert isinstance(writer_retry_job, dict)
    assert writer_retry_job.get("job_id") == writer_failed_job_id
    assert str(writer_retry_job.get("status", "")).lower() in {"queued", "running", "succeeded"}

    queue_status = _call_tool(client, "queue_status", {}, "valid-admin-token")
    assert isinstance(queue_status.get("queue_depth"), int)
    assert isinstance(queue_status.get("active_jobs"), int)
    assert isinstance(queue_status.get("worker_count"), int)


# W28E-1882: the Jobs WebUI list must be able to fetch a lean summary (no heavy
# per-job payload) so a large job history serialises/renders without stalling,
# while the default contract keeps the payload for A2A/automation callers.
_JOB_SUMMARY_COLUMNS = ("job_id", "status", "job_type", "created_at", "user_id")


@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")
def test_job_list_lean_summary_omits_payload(service: IndexService) -> None:
    # Covers: FR-07 (Jobs list summary projection)
    client = TestClient(build_api_app(service=service))

    _ = _call_tool(
        client,
        "admin_collection_create",
        {"profile": "default", "collection": "it1_20_jobs_lean"},
        "valid-admin-token",
    )
    queued = _call_tool(
        client,
        "ingest_text",
        {
            "profile": "default",
            "collection": "it1_20_jobs_lean",
            "text": "job list lean summary payload body that would bloat the list",
            "source": "file://it1_20/jobs-lean.txt",
        },
        "valid-admin-token",
    )
    job_id = str(queued["job_id"])

    # Default list keeps the full payload (backward compatible).
    default_listed = _call_tool(client, "job_list", {"limit": 2000}, "valid-admin-token")
    default_row = next(
        item for item in default_listed["jobs"] if str(item.get("job_id", "")) == job_id
    )
    assert "payload" in default_row

    # Lean list omits the payload but retains every summary column the table renders.
    for lean_arg in (False, "false"):
        lean_listed = _call_tool(
            client,
            "job_list",
            {"limit": 2000, "include_payload": lean_arg},
            "valid-admin-token",
        )
        lean_row = next(
            item for item in lean_listed["jobs"] if str(item.get("job_id", "")) == job_id
        )
        assert "payload" not in lean_row, f"payload leaked with include_payload={lean_arg!r}"
        for column in _JOB_SUMMARY_COLUMNS:
            assert lean_row.get(column), f"lean row missing summary column {column!r}"
        # Owner attribution (used by the RBAC/actor column) survives payload removal.
        assert _job_actor(lean_row) != ""

    # The full record remains reachable for the detail dialog via job_get.
    detail = _call_tool(client, "job_get", {"job_id": job_id}, "valid-admin-token")
    assert isinstance(detail.get("job"), dict)
