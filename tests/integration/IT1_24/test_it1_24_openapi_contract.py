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
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from tests.http_paths import api_tools_path
from tests.live_runtime import LiveIndexRuntime


def _request_json(url: str, *, method: str = "GET", payload: dict[str, object] | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
    encoded = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=encoded, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise AssertionError(f"HTTP {exc.code} for {url}: {detail}") from exc


def test_openapi_and_tool_contract_include_canonical_metadata_fields(
    live_service: LiveIndexRuntime, runtime_mode: str, runtime_endpoints: dict[str, str] | None
) -> None:
    client = TestClient(build_api_app(service=live_service)) if runtime_mode == "local-server" else None

    def get_openapi() -> dict[str, object]:
        if runtime_mode == "local-server":
            assert client is not None
            response = client.get("/openapi.json")
            assert response.status_code == 200, response.text
            return response.json()
        assert runtime_endpoints is not None
        status, body = _request_json(f"{runtime_endpoints['api_base_url']}/openapi.json")
        assert status == 200
        return body

    def call_tool(tool_name: str, payload: dict[str, object], token: str) -> dict[str, object]:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if runtime_mode == "local-server":
            assert client is not None
            response = client.post(api_tools_path(tool_name), json=payload, headers=headers)
            assert response.status_code == 200, response.text
            return response.json()
        assert runtime_endpoints is not None
        status, body = _request_json(
            f"{runtime_endpoints['api_base_url']}{api_tools_path(tool_name)}",
            method="POST",
            payload=payload,
            headers=headers,
        )
        assert status == 200
        return body

    openapi = get_openapi()
    paths = dict(openapi.get("paths", {}))
    assert "/health" in paths
    assert "/app/v1/tools" in paths
    assert "/api/v1/tools" in paths
    assert "/app/v1/upload" in paths

    schemas = dict(dict(openapi.get("components", {})).get("schemas", {}))
    ingest_preview = dict(dict(schemas.get("IngestPreviewOutput", {})).get("properties", {}))
    table_extract = dict(dict(schemas.get("TableExtractOutput", {})).get("properties", {}))
    search_result = dict(dict(schemas.get("SearchResult", {})).get("properties", {}))
    retrieve_output = dict(dict(schemas.get("RetrieveOutput", {})).get("properties", {}))

    for field_name in ("parser_provider", "parser_version", "ocr_engine", "ocr_confidence", "page", "table_id"):
        assert field_name in ingest_preview
    for field_name in ("parser_provider", "page", "table_id"):
        assert field_name in table_extract
    for field_name in ("source_uri", "content_hash", "lifecycle_state", "is_latest"):
        assert field_name in search_result
        assert field_name in retrieve_output

    preview = call_tool(
        "ingest_preview",
        {"text": "contract preview payload", "source_uri": "file://it24/preview.txt", "parser_chain": ["internal"]},
        "valid-writer-token",
    )
    for field_name in ("parser_provider", "ocr_engine", "ocr_confidence", "page", "table_id"):
        assert field_name in preview

    tables = call_tool(
        "table_extract",
        {
            "text": "left|right\n1|2",
            "source_uri": "file://it24/table.txt",
            "parser_chain": ["internal"],
            "table_policy": "table_as_json",
        },
        "valid-admin-token",
    )
    for field_name in ("parser_provider", "page", "table_id"):
        assert field_name in tables

    docs_path = Path(__file__).resolve().parents[3] / "docs" / "API_DOCUMENTATION.md"
    docs_text = docs_path.read_text(encoding="utf-8")
    for required in (
        "| API server | 8074 |",
        "| Web server | 8075 |",
        "| MCP server | 8076 |",
        "| A2A server | 8077 |",
        "openapi.json",
        "parser_provider",
        "ocr_engine",
        "ocr_confidence",
        "table_id",
    ):
        assert required in docs_text
