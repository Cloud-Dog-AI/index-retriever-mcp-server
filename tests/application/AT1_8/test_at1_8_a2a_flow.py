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

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from tests.http_paths import a2a_base_path, a2a_health_path, api_tools_path
from tests.live_runtime import LiveIndexRuntime
import pytest


def _http_get(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
    req = Request(url=url, headers=headers or {}, method="GET")
    try:
        with urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"detail": body}


def _http_post(url: str, payload: dict[str, object], headers: dict[str, str]) -> tuple[int, dict[str, object]]:
    req = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"detail": body}
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.req("FR-004")


def test_a2a_namespace_and_shared_auth_flow(
    live_service: LiveIndexRuntime, runtime_mode: str, runtime_endpoints: dict[str, str] | None
) -> None:
    key = os.environ.get("TEST_A2A_API_KEY", "12345678").strip() or "12345678"
    auth_headers = {"Authorization": f"Bearer {key}"}
    suffix = uuid4().hex[:8]
    collection = f"at_a2a_{suffix}"

    def post_tool(tool_name: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
        if runtime_mode == "local-server":
            client = TestClient(build_api_app(service=live_service))
            response = client.post(api_tools_path(tool_name), json=payload, headers=auth_headers)
            return response.status_code, response.json()
        assert runtime_endpoints is not None
        return _http_post(
            f"{runtime_endpoints['api_base_url']}{api_tools_path(tool_name)}",
            payload,
            {"Content-Type": "application/json", **auth_headers},
        )

    if runtime_mode == "local-server":
        client = TestClient(build_api_app(service=live_service))
        no_auth = client.get(a2a_health_path())
        root = client.get(a2a_base_path(), headers=auth_headers)
        health = client.get(a2a_health_path(), headers=auth_headers)
        assert no_auth.status_code == 401
        assert root.status_code == 200
        assert health.status_code == 200
    else:
        assert runtime_endpoints is not None
        base = runtime_endpoints["api_base_url"]
        no_auth_code, _ = _http_get(f"{base}{a2a_health_path()}")
        root_code, root_body = _http_get(f"{base}{a2a_base_path()}", auth_headers)
        health_code, health_body = _http_get(f"{base}{a2a_health_path()}", auth_headers)
        assert no_auth_code == 401
        assert root_code == 200, root_body
        assert health_code == 200, health_body

    create_code, create = post_tool(
        "admin_collection_create",
        {"profile": "default", "collection": collection},
    )
    assert create_code == 200, create
    assert create.get("status") == "ok"

    delete_code, delete = post_tool(
        "admin_collection_delete",
        {"profile": "default", "collection": collection},
    )
    assert delete_code == 200, delete
    assert delete.get("status") == "ok"
