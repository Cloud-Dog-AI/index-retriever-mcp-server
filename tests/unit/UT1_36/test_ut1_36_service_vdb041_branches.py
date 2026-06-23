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

import asyncio
import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

import index_tools.tools.service as service_mod
from index_tools.tools.service import (
    IndexService,
    ProviderDiagnosticError,
    _descriptor_to_dict,
    _parser_probe,
    _PreviewResult,
    _PreviewVdbBridge,
    _redact_diagnostic_detail,
)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-013") # W28E-1805A semantic binding


def test_redaction_descriptor_and_provider_envelope() -> None:
    @dataclass(slots=True)
    class _Caps:
        filtering: bool
        max_batch_size: int

    assert _descriptor_to_dict(_Caps(filtering=True, max_batch_size=10)) == {
        "filtering": True,
        "max_batch_size": 10,
    }
    redacted = _redact_diagnostic_detail("token=abc123 api_key:top-secret password = hidden")
    assert "[REDACTED]" in redacted

    error = ProviderDiagnosticError(
        operation="ingest_preview",
        provider="internal",
        message="failed",
        detail="token=abc123",
    )
    payload = json.loads(str(error))
    assert payload["error"]["code"] == "PROVIDER_DIAGNOSTIC"
    assert "[REDACTED]" in payload["error"]["detail"]
    assert error.envelope["error"]["provider"] == "internal"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-013") # W28E-1805A semantic binding


def test_preview_bridge_and_parser_probe_helper() -> None:
    @dataclass(slots=True)
    class _Record:
        record_id: str
        content: str
        metadata: dict[str, Any]

    bridge = _PreviewVdbBridge()
    out = asyncio.run(
        bridge.upsert_records(
            "preview",
            [
                _Record(record_id="r1", content="chunk-a", metadata={}),
                _Record(record_id="r2", content="chunk-b", metadata={}),
            ],
            provider_id="internal",
        )
    )
    assert out == ["r1", "r2"]
    assert len(bridge.records) == 2

    class _Provider:
        async def health_check(self) -> bool:
            return True

        async def parse_bytes(self, *_args, **_kwargs) -> Any:
            return SimpleNamespace(text_blocks=["a"], table_blocks=["t1"], quality={"score": 1.0})

    healthy, ir = asyncio.run(
        _parser_probe(
            provider=_Provider(),
            sample_text="hello",
            filename="x.txt",
            source_uri="inline://x.txt",
            mime_type="text/plain",
            options={},
        )
    )
    assert healthy is True
    assert len(ir.text_blocks) == 1
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-013") # W28E-1805A semantic binding


def test_backend_capabilities_and_search_plan_fallback_paths(
    monkeypatch: pytest.MonkeyPatch, service: IndexService
) -> None:
    # Covers: FR-13A
    monkeypatch.setattr(service_mod, "CapabilityDescriptor", None)
    monkeypatch.setattr(service_mod, "vdb_plan_search", None)
    monkeypatch.setattr(service_mod, "SearchRequest", None)

    capabilities = service.backend_capabilities("default")
    assert capabilities["provider_id"] == service.profile_get("default")["backend"]
    assert capabilities["filtering"] is True

    planned = service.search_plan(profile="default", query="alpha", top_k=0)
    assert planned["top_k"] == 1
    with pytest.raises(ValueError):
        service.search_plan(
            profile="default",
            query="alpha",
            top_k=1,
            filters={"tenant": "x"},
            capability_override={"filtering": False},
        )
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-013") # W28E-1805A semantic binding


def test_search_plan_capability_override_and_filter_rejection(
    monkeypatch: pytest.MonkeyPatch, service: IndexService
) -> None:
    @dataclass(slots=True)
    class _Descriptor:
        provider_id: str
        filtering: bool
        hybrid_search: bool
        sparse_vectors: bool
        multi_vector: bool
        metadata_indexing: bool
        upsert_semantics: bool
        delete_by_filter: bool
        ttl_native: bool
        transactions: bool
        consistency: bool
        max_metadata_bytes: int
        max_batch_size: int
        supports_multimodal: bool

    monkeypatch.setattr(service_mod, "CapabilityDescriptor", _Descriptor)

    class _Req:
        def __init__(self, query_text: str, top_k: int, filters: dict[str, Any]) -> None:
            self.query_text = query_text
            self.top_k = top_k
            self.filters = filters

    monkeypatch.setattr(service_mod, "SearchRequest", _Req)
    monkeypatch.setattr(
        service_mod,
        "vdb_plan_search",
        lambda request, _descriptor: {"mode": "vector", "top_k": request.top_k, "filters": {}},
    )

    capability_payload = service.backend_capabilities("default")
    assert capability_payload["provider_id"] == service.profile_get("default")["backend"]

    descriptor = service._build_capability_descriptor("default", capability_override={"max_batch_size": 7})
    assert descriptor.max_batch_size == 7
    with pytest.raises(ValueError):
        service.search_plan(profile="default", query="alpha", top_k=3, filters={"tenant": "x"})
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-013") # W28E-1805A semantic binding


def test_pipeline_preview_unavailable_branch(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
    monkeypatch.setattr(service_mod, "ingest_document", None)
    monkeypatch.setattr(service_mod, "ParserIngestionOptions", None)
    with pytest.raises(ProviderDiagnosticError):
        service._run_pipeline_preview(source=b"payload", source_uri="inline://preview.txt")
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-013") # W28E-1805A semantic binding


def test_pipeline_preview_success_and_failure_branches(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
    class _Options:
        def __init__(self, **kwargs: Any) -> None:
            self.payload = dict(kwargs)

    @dataclass(slots=True)
    class _Record:
        record_id: str
        content: str
        metadata: dict[str, Any]

    async def _ok_ingest(
        bridge: _PreviewVdbBridge,
        collection: str,
        source: bytes | str,
        **kwargs: Any,
    ) -> list[str]:
        _ = source
        metadata = {
            "source_uri": kwargs["source_uri"],
            "filename": "doc.csv",
            "mime_type": "text/csv",
            "parser_provider": "internal",
            "parser_version": "v1",
            "ocr_mode": "disabled",
            "ocr_applied": False,
            "table_policy": "table_as_json",
        }
        await bridge.upsert_records(collection, [_Record(record_id="r1", content="a|b", metadata=metadata)])
        kwargs["on_checkpoint"]("parsed", 1)
        return ["r1"]

    monkeypatch.setattr(service_mod, "ParserIngestionOptions", _Options)
    monkeypatch.setattr(service_mod, "ingest_document", _ok_ingest)
    preview = service._run_pipeline_preview(
        source="payload",
        source_uri="https://example.local/doc.csv",
        parser_chain=["internal"],
    )
    assert preview.record_ids == ["r1"]
    assert preview.metadata["filename"] == "doc.csv"
    assert preview.chunks == ["a|b"]
    assert preview.checkpoints[0]["stage"] == "parsed"

    async def _bad_ingest(*_args: Any, **_kwargs: Any) -> list[str]:
        raise RuntimeError("token=supersecret")

    monkeypatch.setattr(service_mod, "ingest_document", _bad_ingest)
    with pytest.raises(ProviderDiagnosticError) as exc:
        service._run_pipeline_preview(source="payload", source_uri="inline://bad.txt", parser_chain=["internal"])
    assert "[REDACTED]" in str(exc.value)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-013") # W28E-1805A semantic binding


def test_parsers_list_and_parser_test_branches(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
    monkeypatch.setattr(service_mod, "build_parser_registry", None)
    assert service.parsers_list() == []
    with pytest.raises(ProviderDiagnosticError):
        service.parser_test("internal")

    @dataclass(slots=True)
    class _Caps:
        parse_bytes: bool = True

    provider = SimpleNamespace(provider_id="internal", provider_version="1.0", capabilities=_Caps())

    class _Registry:
        def list_ids(self) -> list[str]:
            return ["internal", "missing"]

        def get(self, provider_id: str) -> Any:
            if provider_id == "internal":
                return provider
            return None

    monkeypatch.setattr(service_mod, "build_parser_registry", lambda _services=None: _Registry())
    parsers = service.parsers_list()
    assert len(parsers) == 1
    assert parsers[0]["provider_id"] == "internal"

    with pytest.raises(ValueError):
        service.parser_test("missing")

    async def _probe_fail(**_kwargs: Any) -> tuple[bool, Any]:
        raise RuntimeError("password=bad")

    monkeypatch.setattr(service_mod, "_parser_probe", _probe_fail)
    with pytest.raises(ProviderDiagnosticError) as exc:
        service.parser_test("internal")
    assert "[REDACTED]" in str(exc.value)

    async def _probe_ok(**_kwargs: Any) -> tuple[bool, Any]:
        ir = SimpleNamespace(text_blocks=["a", "b"], table_blocks=["t"], quality={"confidence": 0.9})
        return True, ir

    monkeypatch.setattr(service_mod, "_parser_probe", _probe_ok)
    result = service.parser_test("internal")
    assert result["healthy"] is True
    assert result["text_blocks"] == 2
    assert result["table_blocks"] == 1
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-013") # W28E-1805A semantic binding


def test_wrapper_tools_and_ocr_paths(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
    # Covers: FR-09, FR-P001, FR-13B
    preview_with_table = _PreviewResult(
        record_ids=["r1"],
        metadata={
            "source_uri": "inline://preview.txt",
            "filename": "preview.txt",
            "mime_type": "text/plain",
            "parser_provider": "internal",
            "parser_version": "1.0",
            "ocr_mode": "disabled",
            "ocr_applied": False,
            "table_policy": "table_as_json",
        },
        chunks=["a|b", "plain text"],
        checkpoints=[{"stage": "ingest", "count": 1}],
    )
    monkeypatch.setattr(IndexService, "_run_pipeline_preview", lambda self, **_kwargs: preview_with_table)

    ingest_preview = service.ingest_preview(text="payload")
    assert ingest_preview["chunk_count"] == 2
    assert ingest_preview["parser_provider"] == "internal"

    extracted = service.extract_only(text="payload")
    assert extracted["chunk_count"] == 2
    assert "a|b" in extracted["text"]

    table = service.table_extract(text="payload")
    assert table["table_count"] == 1
    assert table["tables"][0] == "a|b"

    preview_without_table = _PreviewResult(
        record_ids=["r2"],
        metadata={"parser_provider": "internal"},
        chunks=["plain chunk"],
        checkpoints=[],
    )
    monkeypatch.setattr(IndexService, "_run_pipeline_preview", lambda self, **_kwargs: preview_without_table)
    fallback = service.table_extract(text="payload")
    assert fallback["table_count"] == 1
    assert fallback["tables"][0] == "plain chunk"

    monkeypatch.setattr(service_mod, "decide_ocr", None)
    forced = service.ocr_run(text="tiny", mode="force", provider_id="ocr-provider")
    assert forced["enabled"] is True
    assert forced["reason"] == "mode_force"

    monkeypatch.setattr(
        service_mod,
        "decide_ocr",
        lambda **kwargs: SimpleNamespace(
            enabled=False,
            mode=kwargs["mode"],
            reason="heuristic_skip",
            provider_id=kwargs["provider_id"],
        ),
    )
    decision = service.ocr_run(text="tiny", mode="auto", provider_id="ocr-provider")
    assert decision["enabled"] is False
    assert decision["reason"] == "heuristic_skip"
