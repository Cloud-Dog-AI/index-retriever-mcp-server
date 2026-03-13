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

# index-retriever-mcp-server — IT2.13
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: OCR-capable parser matrix on image-heavy PDF corpus.

from __future__ import annotations

import asyncio
import os
import time

import pytest

from tests.integration.it2_matrix_helpers import parse_pdf_with_provider
from tests.w23a_helpers import corpus_file, parser_available, write_artifact_json


def _is_soft_provider_unavailable(error: str) -> bool:
    text = str(error).strip().lower()
    return (
        "busy retries exhausted" in text
        or "provider busy" in text
        or "queue" in text and "busy" in text
        or "endpoint unavailable (route not found)" in text
    )


def _provider_timeout_seconds(provider_id: str) -> float:
    provider = provider_id.strip().lower()
    if provider == "marker_mcp":
        return float(os.getenv("MARKER_MCP_DOC_TIMEOUT_SECONDS", os.getenv("MARKER_MCP_TIMEOUT_SECONDS", "1200")) or 1200)
    if provider == "mineru":
        return float(os.getenv("MINERU_DOC_TIMEOUT_SECONDS", os.getenv("MINERU_TIMEOUT_SECONDS", "240")) or 240)
    return float(os.getenv("PARSER_PROVIDER_TIMEOUT_SECONDS", "240") or 240)


def test_it2_13_ocr_capable_parser_matrix_extracts_text() -> None:
    image_pdf = corpus_file("Handwritten-Concern-Form-reporting-Domestic-Abuse-Good-Example.pdf", "Examples.pdf")
    providers = [
        provider_id
        for provider_id in ("mineru", "marker_mcp", "transformers", "docling", "deepdoc")
        if parser_available(provider_id)
    ]
    if not providers:
        pytest.fail("No OCR-capable parser providers are configured", pytrace=False)

    results: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    for provider_id in providers:
        timeout_seconds = _provider_timeout_seconds(provider_id)
        started = time.perf_counter()
        try:
            payload = asyncio.run(
                asyncio.wait_for(
                    parse_pdf_with_provider(provider_id, source_path=image_pdf),
                    timeout=timeout_seconds,
                )
            )
        except TimeoutError:
            elapsed = time.perf_counter() - started
            errors.append(
                {
                    "provider_id": provider_id,
                    "elapsed_seconds": round(elapsed, 2),
                    "timeout_seconds": timeout_seconds,
                    "error": f"timed out after {timeout_seconds:.1f}s for {image_pdf.name}",
                }
            )
            continue
        except Exception as exc:
            elapsed = time.perf_counter() - started
            errors.append(
                {
                    "provider_id": provider_id,
                    "elapsed_seconds": round(elapsed, 2),
                    "timeout_seconds": timeout_seconds,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        elapsed = time.perf_counter() - started
        results.append(
            {
                "provider_id": provider_id,
                "elapsed_seconds": round(elapsed, 2),
                "timeout_seconds": timeout_seconds,
                "text_chars": int(payload["text_chars"]),
                "text_blocks": int(payload["text_blocks"]),
                "quality": dict(payload["quality"]),
            }
        )

    assert results
    assert all(int(item["text_chars"]) > 0 for item in results)
    _ = write_artifact_json(
        "W23A-IT2.13-ocr-matrix.json",
        {"file": image_pdf.name, "results": results, "errors": errors},
    )
    if errors:
        soft_errors = [item for item in errors if _is_soft_provider_unavailable(str(item.get("error", "")))]
        fatal_errors = [item for item in errors if item not in soft_errors]
        _ = write_artifact_json(
            "W23A-IT2.13-ocr-matrix.json",
            {
                "file": image_pdf.name,
                "results": results,
                "errors": errors,
                "soft_errors": soft_errors,
                "fatal_errors": fatal_errors,
            },
        )
        if fatal_errors:
            summary = "; ".join(f"{item['provider_id']} -> {item['error']}" for item in fatal_errors)
            pytest.fail(f"One or more OCR providers failed: {summary}", pytrace=False)
        if not results:
            summary = "; ".join(f"{item['provider_id']} -> {item['error']}" for item in soft_errors)
            pytest.fail(f"No OCR providers completed successfully: {summary}", pytrace=False)
