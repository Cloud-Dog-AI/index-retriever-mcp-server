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

from pathlib import Path

import pytest

from index_tools.tools.service import IndexService
from tests.w23a_helpers import corpus_file, parser_available, parser_services_config


def _run_pdf_preview(service: IndexService, pdf_path: Path) -> tuple[str, object]:
    providers = [
        provider_id
        for provider_id in ("marker_mcp", "mineru", "transformers", "docling", "deepdoc")
        if parser_available(provider_id)
    ]
    if not providers:
        pytest.fail("No parser providers are configured for provenance validation", pytrace=False)

    errors: list[str] = []
    for provider_id in providers:
        try:
            preview = service._run_pipeline_preview(
                source=pdf_path.read_bytes(),
                source_uri=f"file://{pdf_path.name}",
                parser_chain=[provider_id],
                parser_services=parser_services_config(),
                ocr_mode="auto",
                table_policy="table_as_json",
            )
            return provider_id, preview
        except Exception as exc:
            errors.append(f"{provider_id}:{type(exc).__name__}:{exc}")
    pytest.fail("All parser providers failed for provenance validation: " + " | ".join(errors), pytrace=False)


def test_plain_text_provenance_contract_fields(service: IndexService) -> None:
    preview = service.ingest_preview(
        text="plain text provenance payload",
        source_uri="file://integration/plain-provenance.txt",
        parser_chain=["internal"],
        ocr_mode="disabled",
        table_policy="table_as_json",
    )

    assert preview["parser_provider"] == "internal"
    assert "ocr_engine" in preview
    assert "ocr_confidence" in preview
    assert "page" in preview
    assert "table_id" in preview


def test_pdf_ocr_and_table_provenance_fields_recorded(service: IndexService) -> None:
    ocr_pdf = corpus_file(
        "Handwritten-Concern-Form-reporting-Domestic-Abuse-Good-Example.pdf",
        "Examples.pdf",
    )
    provider_id, preview = _run_pdf_preview(service, ocr_pdf)
    metadata = dict(preview.metadata)

    assert metadata.get("parser_provider") == provider_id
    assert "ocr_engine" in metadata
    assert "ocr_confidence" in metadata
    assert "page" in metadata or "page_number" in metadata
    assert preview.checkpoints

    table_pdf = corpus_file(
        "Examples.pdf",
        "IBRD-Financial-Statements-June-2025.pdf",
        "NIST.SP.800-53r5.pdf",
    )
    _, table_preview = _run_pdf_preview(service, table_pdf)
    table_metadata = dict(table_preview.metadata)
    assert "table_id" in table_metadata
    assert "page" in table_metadata or "page_number" in table_metadata
    assert table_preview.chunks


def test_reingest_provenance_is_preserved_not_overwritten(service: IndexService) -> None:
    pdf = corpus_file(
        "Handwritten-Concern-Form-reporting-Domestic-Abuse-Good-Example.pdf",
        "Examples.pdf",
    )
    _, first_preview = _run_pdf_preview(service, pdf)
    _, second_preview = _run_pdf_preview(service, pdf)

    first_metadata = dict(first_preview.metadata)
    replay_preview = service._run_pipeline_preview(
        source=pdf.read_bytes(),
        source_uri=f"file://{pdf.name}",
        parser_chain=[str(first_metadata.get("parser_provider", "internal"))],
        parser_services=parser_services_config(),
        metadata=first_metadata,
        ocr_mode="auto",
        table_policy="table_as_json",
    )
    replay_metadata = dict(replay_preview.metadata)

    for key in ("parser_provider", "parser_version", "ocr_engine", "ocr_confidence", "page", "table_id"):
        if first_metadata.get(key) not in ("", None):
            assert replay_metadata.get(key) == first_metadata.get(key)
        if second_preview.metadata.get(key) not in ("", None):
            assert replay_metadata.get(key) in {first_metadata.get(key), second_preview.metadata.get(key)}
