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
import pytest

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService
from tests.http_paths import api_tools_path


def _call_tool(client: TestClient, tool_name: str, payload: dict[str, object], token: str) -> dict[str, object]:
    response = client.post(
        api_tools_path(tool_name),
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_job_management_tools_contract(service: IndexService) -> None:
    # Covers: FR-07
    client = TestClient(build_api_app(service=service))

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
    assert queued["status"] == "queued"

    listed = _call_tool(client, "job_list", {}, "valid-admin-token")
    jobs = listed.get("jobs")
    assert isinstance(jobs, list)
    assert any(str(item.get("job_id", "")) == job_id for item in jobs)

    succeeded_only = _call_tool(client, "job_list", {"status": "succeeded"}, "valid-admin-token")
    succeeded_jobs = succeeded_only.get("jobs")
    assert isinstance(succeeded_jobs, list)
    assert any(str(item.get("job_id", "")) == job_id for item in succeeded_jobs)

    cancelled = _call_tool(client, "job_cancel", {"job_id": job_id}, "valid-admin-token")
    cancelled_job = cancelled.get("job")
    assert isinstance(cancelled_job, dict)
    assert cancelled_job.get("job_id") == job_id
    assert str(cancelled_job.get("status", "")).lower() == "cancelled"

    original_upsert = service.vdb.upsert_records

    async def _fail_upsert(*args, **kwargs):
        _ = args, kwargs
        raise RuntimeError("forced embed failure for IT1.20 retry path")

    service.vdb.upsert_records = _fail_upsert
    with pytest.raises(RuntimeError, match="forced embed failure"):
        _ = service.ingest_text(
            profile="default",
            collection="it1_20_jobs",
            text="job management forced failure payload",
            source="file://it1_20/jobs-failed.txt",
            actor="integration",
        )
    service.vdb.upsert_records = original_upsert

    failed_list = _call_tool(client, "job_list", {"status": "dead_lettered"}, "valid-admin-token")
    failed_jobs = failed_list.get("jobs")
    assert isinstance(failed_jobs, list)
    assert failed_jobs, "Expected at least one failed job from forced failure path"
    failed_job_id = str(failed_jobs[-1]["job_id"])

    retried = _call_tool(client, "job_retry", {"job_id": failed_job_id}, "valid-admin-token")
    retried_job = retried.get("job")
    assert isinstance(retried_job, dict)
    assert retried_job.get("job_id") == failed_job_id
    assert str(retried_job.get("status", "")).lower() in {"queued", "running", "succeeded"}

    queue_status = _call_tool(client, "queue_status", {}, "valid-admin-token")
    assert isinstance(queue_status.get("queue_depth"), int)
    assert isinstance(queue_status.get("active_jobs"), int)
    assert isinstance(queue_status.get("worker_count"), int)
