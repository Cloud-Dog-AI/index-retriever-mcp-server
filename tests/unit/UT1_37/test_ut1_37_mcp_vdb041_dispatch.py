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

    def retrieve(
        self,
        doc_id: str,
        profile: str | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            ("retrieve", {"doc_id": doc_id, "profile": profile, "collection": collection})
        )
        return {"doc_id": doc_id, "record_id": doc_id, "metadata": {"content_hash": "hash"}}

    def search_plan(self, profile: str, query: str, top_k: int, filters: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(
            (
                "search_plan",
                {"profile": profile, "query": query, "top_k": top_k, "filters": dict(filters)},
            )
        )
        return {"mode": "vector", "top_k": top_k, "filters": dict(filters)}

    def search(
        self,
        profile: str,
        collection: str,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        payload = {
            "profile": profile,
            "collection": collection,
            "query": query,
            "top_k": top_k,
            "filters": dict(filters or {}),
        }
        self.calls.append(("search", payload))
        return [
            {
                "doc_id": "record-1",
                "chunk_id": "chunk-1",
                "score": 0.75,
                "metadata": {"collection": collection},
            }
        ]

    def delete_by_id(self, profile: str, collection: str, doc_id: str) -> bool:
        self.calls.append(
            ("delete_by_id", {"profile": profile, "collection": collection, "doc_id": doc_id})
        )
        return True

    def delete_by_filter(self, profile: str, collection: str, filters: dict[str, Any]) -> int:
        self.calls.append(
            ("delete_by_filter", {"profile": profile, "collection": collection, "filters": dict(filters)})
        )
        return 2

    def retention_run(self, profile: str, collection: str, older_than_days: int) -> int:
        self.calls.append(
            (
                "retention_run",
                {"profile": profile, "collection": collection, "older_than_days": older_than_days},
            )
        )
        return 1

    def reindex_run(self, profile: str, collection: str) -> dict[str, int]:
        self.calls.append(("reindex_run", {"profile": profile, "collection": collection}))
        return {"documents": 3}


def test_required_roles_for_new_wrapper_tools() -> None:
    assert mcp_server._required_permission_for_tool("parsers_list") == "collection.read"
    assert mcp_server._required_permission_for_tool("parser_test") == "source.configure"
    assert mcp_server._required_permission_for_tool("extract_only") == "collection.write"


def test_execute_tool_dispatches_vdb_wrapper_calls() -> None:
    # Covers: FR-13B
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

    retrieved = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "retrieve",
        {"profile": "default", "collection": "docs", "doc_id": "record-1"},
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"reader"},
    )
    assert retrieved["doc_id"] == "record-1"

    deleted_by_id = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "delete_by_id",
        {"profile": "default", "collection": "docs", "doc_id": "record-2"},
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"admin"},
    )
    assert deleted_by_id == {"deleted": True, "status": "ok"}

    deleted_by_filter = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "delete_by_filter",
        {"profile": "default", "collection": "docs", "filters": {"source_uri": "file://match.txt"}},
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"admin"},
    )
    assert deleted_by_filter == {"deleted": 2, "status": "ok"}

    retention = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "retention_run",
        {"profile": "default", "collection": "docs", "older_than_days": "30"},
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"admin"},
    )
    assert retention == {"deleted": 1, "status": "ok"}

    reindex = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "reindex_run",
        {"profile": "default", "collection": "docs"},
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"admin"},
    )
    assert reindex == {"documents": 3, "status": "ok"}

    names = [name for name, _payload in service.calls]
    assert names == [
        "parsers_list",
        "parser_test",
        "ingest_preview",
        "extract_only",
        "ocr_run",
        "table_extract",
        "retrieve",
        "delete_by_id",
        "delete_by_filter",
        "retention_run",
        "reindex_run",
    ]


def test_execute_tool_search_explain_returns_plan_and_scoring_metadata() -> None:
    # Covers: FR-P002
    service = _ToolService()
    registry = SimpleNamespace(get=lambda _name: None)

    explained = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "search_explain",
        {
            "profile": "default",
            "collection": "docs",
            "query": "alpha",
            "top_k": 3,
            "filters": {"tenant_id": "acme"},
        },
        registry=registry,  # type: ignore[arg-type]
        identity_roles={"reader"},
    )

    assert explained["query"] == "alpha"
    assert explained["profile"] == "default"
    assert explained["collection"] == "docs"
    assert explained["plan"] == {"mode": "vector", "top_k": 3, "filters": {"tenant_id": "acme"}}
    assert explained["results"] == [
        {
            "doc_id": "record-1",
            "chunk_id": "chunk-1",
            "score": 0.75,
            "metadata": {"collection": "docs"},
            "similarity": {"score": 0.75, "mode": "vector", "top_k": 3},
        }
    ]

    names = [name for name, _payload in service.calls]
    assert names == ["search_plan", "search"]
