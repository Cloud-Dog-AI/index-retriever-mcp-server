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

import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from tests.http_paths import api_tools_path
from tests.live_runtime import LiveIndexRuntime


def _post_json(url: str, payload: dict[str, object], headers: dict[str, str]) -> tuple[int, dict[str, object]]:
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise AssertionError(f"HTTP {exc.code} for {url}: {detail}") from exc
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_mcp_tool_execution(
    live_service: LiveIndexRuntime, runtime_mode: str, runtime_endpoints: dict[str, str] | None
) -> None:
    # Covers: FR-P002
    client = TestClient(build_api_app(service=live_service)) if runtime_mode == "local-server" else None
    admin_headers = {"authorization": "Bearer valid-admin-token"}
    writer_headers = {"authorization": "Bearer valid-writer-token"}
    reader_headers = {"authorization": "Bearer valid-reader-token"}

    suffix = uuid4().hex[:8]
    primary_collection = f"it_mcp_{suffix}"
    iso_a = f"it_iso_a_{suffix}"
    iso_b = f"it_iso_b_{suffix}"

    def call_tool(tool_name: str, payload: dict[str, object], headers: dict[str, str]) -> dict[str, object]:
        if runtime_mode == "local-server":
            assert client is not None
            response = client.post(api_tools_path(tool_name), json=payload, headers=headers)
            assert response.status_code == 200, response.text
            return response.json()

        assert runtime_endpoints is not None
        merged_headers = dict(headers)
        merged_headers["Content-Type"] = "application/json"
        status, body = _post_json(
            f"{runtime_endpoints['api_base_url']}{api_tools_path(tool_name)}",
            payload,
            merged_headers,
        )
        assert status == 200, body
        return body

    create_payload = {"profile": "default", "collection": primary_collection}
    created_once = call_tool("admin_collection_create", create_payload, admin_headers)
    assert created_once.get("status") == "ok"
    created_twice = call_tool("admin_collection_create", create_payload, admin_headers)
    assert created_twice.get("status") == "ok"

    listed = call_tool("collections_list", {"profile": "default"}, reader_headers)
    assert primary_collection in listed["collections"]

    ingested = call_tool(
        "ingest_text",
        {
            "profile": "default",
            "collection": primary_collection,
            "text": "The quick brown fox jumps over the lazy dog",
            "source": "test:w8c:step4",
        },
        writer_headers,
    )
    assert str(ingested.get("status", "")).lower() in {"queued", "running", "succeeded"}
    job_id = str(ingested.get("job_id", ""))
    assert job_id

    deadline = time.monotonic() + 30
    job_status = str(ingested.get("status", "")).lower()
    while job_status in {"queued", "running"} and time.monotonic() < deadline:
        job_detail = call_tool("job_get", {"job_id": job_id}, writer_headers)
        job = job_detail.get("job")
        assert isinstance(job, dict)
        job_status = str(job.get("status", "")).lower()
        if job_status in {"queued", "running"}:
            time.sleep(0.1)
    assert job_status == "succeeded"

    search = call_tool(
        "search",
        {
            "profile": "default",
            "collection": primary_collection,
            "query": "The quick brown fox jumps over the lazy dog",
            "top_k": 5,
        },
        reader_headers,
    )
    results = search.get("results", [])
    assert results
    assert any(float(row.get("score", 0.0)) > 0 for row in results)
    assert any((row.get("metadata") or {}).get("source") == "test:w8c:step4" for row in results)
    assert any((row.get("metadata") or {}).get("source_uri") == "test:w8c:step4" for row in results)
    assert any((row.get("metadata") or {}).get("filename") in {"test:w8c:step4", "w8c:step4"} for row in results)
    assert any((row.get("metadata") or {}).get("mime_type") == "text/plain" for row in results)

    explained = call_tool(
        "search_explain",
        {
            "profile": "default",
            "collection": primary_collection,
            "query": "The quick brown fox jumps over the lazy dog",
            "top_k": 5,
        },
        reader_headers,
    )
    assert explained.get("query") == "The quick brown fox jumps over the lazy dog"
    assert explained.get("profile") == "default"
    assert explained.get("collection") == primary_collection
    assert isinstance(explained.get("plan"), dict)
    assert explained["plan"].get("mode") in {"vector", "hybrid"}
    explained_results = explained.get("results", [])
    assert explained_results
    assert any("similarity" in row for row in explained_results)
    assert any(float((row.get("similarity") or {}).get("score", 0.0)) > 0 for row in explained_results)
    assert any((row.get("metadata") or {}).get("collection") == primary_collection for row in explained_results)

    _ = call_tool("admin_collection_create", {"profile": "default", "collection": iso_a}, admin_headers)
    _ = call_tool("admin_collection_create", {"profile": "default", "collection": iso_b}, admin_headers)
    _ = call_tool(
        "ingest_text",
        {"profile": "default", "collection": iso_a, "text": "alpha unique token", "source": "test:w8c:iso:a"},
        writer_headers,
    )
    _ = call_tool(
        "ingest_text",
        {"profile": "default", "collection": iso_b, "text": "beta unique token", "source": "test:w8c:iso:b"},
        writer_headers,
    )

    a_rows = call_tool(
        "search", {"profile": "default", "collection": iso_a, "query": "unique token", "top_k": 5}, reader_headers
    )["results"]
    b_rows = call_tool(
        "search", {"profile": "default", "collection": iso_b, "query": "unique token", "top_k": 5}, reader_headers
    )["results"]
    assert a_rows and b_rows
    assert all((row.get("metadata") or {}).get("collection") == iso_a for row in a_rows)
    assert all((row.get("metadata") or {}).get("collection") == iso_b for row in b_rows)

    _ = call_tool("admin_collection_delete", {"profile": "default", "collection": primary_collection}, admin_headers)
    _ = call_tool("admin_collection_delete", {"profile": "default", "collection": iso_a}, admin_headers)
    _ = call_tool("admin_collection_delete", {"profile": "default", "collection": iso_b}, admin_headers)
