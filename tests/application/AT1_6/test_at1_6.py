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

# index-retriever-mcp-server — AT1.6
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Runtime-matrix API/MCP transport workflow.

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_server.mcp_server import build_mcp_app
from tests.http_paths import api_tools_path, mcp_tools_path
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
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise AssertionError(f"HTTP {exc.code} for {url}: {detail}") from exc


def test_runtime_matrix_api_and_mcp_transport(
    live_service: LiveIndexRuntime, runtime_mode: str, runtime_endpoints: dict[str, str] | None
) -> None:
    api_client = TestClient(build_api_app(service=live_service)) if runtime_mode == "local-server" else None
    mcp_client = TestClient(build_mcp_app()) if runtime_mode == "local-server" else None

    suffix = uuid4().hex[:8]
    collection = f"at_runtime_{suffix}"
    source = f"at:runtime:{suffix}"

    def api_tool(tool_name: str, payload: dict[str, object], token: str) -> dict[str, object]:
        headers = {"Authorization": f"Bearer {token}"}
        if runtime_mode == "local-server":
            assert api_client is not None
            response = api_client.post(api_tools_path(tool_name), json=payload, headers=headers)
            assert response.status_code == 200, response.text
            return response.json()
        assert runtime_endpoints is not None
        headers["Content-Type"] = "application/json"
        status, body = _post_json(f"{runtime_endpoints['api_base_url']}{api_tools_path(tool_name)}", payload, headers)
        assert status == 200, body
        return body

    def mcp_tool(tool_name: str, payload: dict[str, object]) -> dict[str, object]:
        headers = {"X-API-Key": "test-api-key"}
        if runtime_mode == "local-server":
            assert mcp_client is not None
            response = mcp_client.post(mcp_tools_path(tool_name), json=payload, headers=headers)
            assert response.status_code == 200, response.text
            body = response.json()
        else:
            assert runtime_endpoints is not None
            headers["Content-Type"] = "application/json"
            status, body = _post_json(
                f"{runtime_endpoints['mcp_base_url']}{mcp_tools_path(tool_name)}", payload, headers
            )
            assert status == 200, body
        assert body.get("ok") is True
        return body["data"]

    created = api_tool("admin_collection_create", {"profile": "default", "collection": collection}, "valid-admin-token")
    assert created.get("status") == "ok"

    queued = api_tool(
        "ingest_text",
        {
            "profile": "default",
            "collection": collection,
            "text": "runtime matrix endpoint payload",
            "source": source,
        },
        "valid-writer-token",
    )
    assert queued.get("status") == "queued"
    assert queued.get("job_id")

    profiles = mcp_tool("profiles_list", {})
    assert "default" in profiles.get("profiles", [])

    deleted = api_tool("admin_collection_delete", {"profile": "default", "collection": collection}, "valid-admin-token")
    assert deleted.get("status") == "ok"
