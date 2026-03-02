# index-retriever-mcp-server — IT1.17
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tool-catalogue wrapper execution coverage for parser/OCR/table helpers.

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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


def test_tool_catalogue_wrappers_execute(
    live_service: LiveIndexRuntime, runtime_mode: str, runtime_endpoints: dict[str, str] | None
) -> None:
    client = TestClient(build_api_app(service=live_service)) if runtime_mode == "local-server" else None

    def call_tool(tool_name: str, payload: dict[str, object], token: str) -> dict[str, object]:
        headers = {"Authorization": f"Bearer {token}"}
        if runtime_mode == "local-server":
            assert client is not None
            response = client.post(api_tools_path(tool_name), json=payload, headers=headers)
            assert response.status_code == 200, response.text
            return response.json()

        assert runtime_endpoints is not None
        headers["Content-Type"] = "application/json"
        status, body = _post_json(f"{runtime_endpoints['api_base_url']}{api_tools_path(tool_name)}", payload, headers)
        assert status == 200, body
        return body

    parsers = call_tool("parsers_list", {}, "valid-reader-token")
    assert parsers.get("parsers")
    assert any(item.get("provider_id") == "internal" for item in parsers["parsers"])

    preview = call_tool(
        "ingest_preview",
        {"text": "preview wrapper payload", "source_uri": "file://it17/preview.txt", "parser_chain": ["internal"]},
        "valid-writer-token",
    )
    assert int(preview.get("chunk_count", 0)) >= 1
    assert preview.get("parser_provider") == "internal"

    extract = call_tool(
        "extract_only",
        {"text": "extract wrapper payload", "source_uri": "file://it17/extract.txt", "parser_chain": ["internal"]},
        "valid-writer-token",
    )
    assert "extract wrapper payload" in str(extract.get("text", ""))

    parser_test = call_tool(
        "parser_test",
        {"provider_id": "internal", "sample_text": "parser test payload", "source_uri": "file://it17/parser.txt"},
        "valid-admin-token",
    )
    assert parser_test.get("healthy") is True

    ocr = call_tool(
        "ocr_run",
        {"text": "ocr wrapper payload", "mode": "auto", "provider_id": "ocr-provider-test", "scanned_ratio": 0.95},
        "valid-admin-token",
    )
    assert "enabled" in ocr
    assert ocr.get("provider_id") == "ocr-provider-test"

    table = call_tool(
        "table_extract",
        {
            "text": "a|b\n1|2",
            "source_uri": "file://it17/table.txt",
            "parser_chain": ["internal"],
            "table_policy": "table_as_json",
        },
        "valid-admin-token",
    )
    assert int(table.get("table_count", 0)) >= 1
