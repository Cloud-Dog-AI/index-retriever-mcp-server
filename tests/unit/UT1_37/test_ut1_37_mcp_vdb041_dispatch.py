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

# index-retriever-mcp-server — UT1.37
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Branch coverage for MCP role mapping and VDB 0.4.1 wrapper dispatch.

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from index_server import mcp_server


class _ToolService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def parsers_list(self, parser_services=None) -> list[dict[str, str]]:
        self.calls.append(("parsers_list", {"parser_services": parser_services}))
        return [{"provider_id": "internal"}]

    def parser_test(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("parser_test", dict(kwargs)))
        return {"healthy": True, "provider_id": kwargs["provider_id"]}

    def ingest_preview(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("ingest_preview", dict(kwargs)))
        return {"chunk_count": 1, "source_uri": kwargs["source_uri"]}

    def extract_only(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("extract_only", dict(kwargs)))
        return {"chunk_count": 1, "text": kwargs["text"]}

    def ocr_run(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("ocr_run", dict(kwargs)))
        return {"enabled": True, "provider_id": kwargs["provider_id"]}

    def table_extract(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("table_extract", dict(kwargs)))
        return {"table_count": 1, "source_uri": kwargs["source_uri"]}


def test_required_roles_for_new_wrapper_tools() -> None:
    assert mcp_server._required_roles_for_tool("parsers_list") == {"reader", "writer", "maintainer", "admin"}
    assert mcp_server._required_roles_for_tool("parser_test") == {"maintainer", "admin"}
    assert mcp_server._required_roles_for_tool("extract_only") == {"writer", "maintainer", "admin"}


def test_execute_tool_dispatches_vdb_wrapper_calls() -> None:
    service = _ToolService()
    registry = SimpleNamespace(get=lambda _name: None)

    parsers = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "parsers_list",
        {"parser_services": {"deepdoc": {"url": "http://localhost"}}},
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"reader"},
    )
    assert parsers["parsers"][0]["provider_id"] == "internal"

    parser_test = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "parser_test",
        {"provider_id": "internal", "sample_text": "hello"},
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"maintainer"},
    )
    assert parser_test["healthy"] is True

    preview = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "ingest_preview",
        {"text": "hello", "source_uri": "inline://preview.txt", "parser_chain": ["internal"]},
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"writer"},
    )
    assert preview["chunk_count"] == 1

    extract = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "extract_only",
        {"text": "hello", "source_uri": "inline://extract.txt", "parser_chain": ["internal"]},
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"writer"},
    )
    assert extract["text"] == "hello"

    ocr = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "ocr_run",
        {
            "text": "hello",
            "mode": "auto",
            "provider_id": "ocr-provider",
            "min_chars": "50",
            "min_scanned_ratio": "0.4",
            "scanned_ratio": "0.8",
        },
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"maintainer"},
    )
    assert ocr["enabled"] is True

    table = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "table_extract",
        {"text": "a|b", "source_uri": "inline://table.txt", "table_policy": "table_as_json"},
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"maintainer"},
    )
    assert table["table_count"] == 1

    names = [name for name, _payload in service.calls]
    assert names == [
        "parsers_list",
        "parser_test",
        "ingest_preview",
        "extract_only",
        "ocr_run",
        "table_extract",
    ]
