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
from urllib.request import Request, urlopen

from fastapi.testclient import TestClient

from index_server.mcp_server import build_mcp_app, build_registry, list_tool_names
from tests.http_paths import mcp_tools_path
from tests.live_runtime import LiveIndexRuntime
import pytest
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_mcp_tool_catalogue(
    live_service: LiveIndexRuntime, runtime_mode: str, runtime_endpoints: dict[str, str] | None
) -> None:
    assert live_service.backend_health_check(provider_id="chroma") is True
    names_direct = list_tool_names(build_registry())
    required_tools = [
        "admin_collection_create",
        "ingest_text",
        "search",
        "parsers_list",
        "parser_test",
        "ingest_preview",
        "extract_only",
        "ocr_run",
        "table_extract",
    ]
    for required in required_tools:
        assert required in names_direct

    if runtime_mode == "local-server":
        client = TestClient(build_mcp_app(service=live_service))
        response = client.get(mcp_tools_path(), headers={"X-API-Key": "test-api-key"})
        assert response.status_code == 200
        payload = response.json()
    else:
        assert runtime_endpoints is not None
        req = Request(
            f"{runtime_endpoints['mcp_base_url']}{mcp_tools_path()}",
            headers={"X-API-Key": "test-api-key"},
            method="GET",
        )
        with urlopen(req, timeout=30) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode("utf-8"))

    names = [tool["name"] for tool in payload["data"]]
    for required in required_tools:
        assert required in names
