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


def _call(
    client: TestClient,
    tool_name: str,
    payload: dict[str, object],
    token: str,
) -> tuple[int, dict[str, object]]:
    response = client.post(
        api_tools_path(tool_name),
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    return response.status_code, body


def test_collection_level_rbac_enforced(service: IndexService) -> None:
    # Covers: FR-05
    client = TestClient(build_api_app(service=service))
    profile = "default"
    collection = "it1_21_restricted"

    status, body = _call(
        client,
        "admin_collection_create",
        {
            "profile": profile,
            "collection": collection,
            "allowed_roles": ["writer", "admin"],
        },
        "valid-admin-token",
    )
    assert status == 200, body
    assert body.get("status") == "ok"

    status, body = _call(
        client,
        "ingest_text",
        {
            "profile": profile,
            "collection": collection,
            "text": "restricted collection RBAC payload",
            "source": "file://it1_21/restricted.txt",
        },
        "valid-writer-token",
    )
    assert status == 200, body
    assert body.get("status") == "queued"

    status, body = _call(
        client,
        "search",
        {
            "profile": profile,
            "collection": collection,
            "query": "RBAC payload",
            "top_k": 5,
        },
        "valid-reader-token",
    )
    assert status == 403, body
    assert "Authorisation failed for collection" in str(body.get("detail", ""))

    status, body = _call(
        client,
        "search",
        {
            "profile": profile,
            "collection": collection,
            "query": "RBAC payload",
            "top_k": 5,
        },
        "valid-writer-token",
    )
    assert status == 200, body
    results = body.get("results")
    assert isinstance(results, list)
    assert results
