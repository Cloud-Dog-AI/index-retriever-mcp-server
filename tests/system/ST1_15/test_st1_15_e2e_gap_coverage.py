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

"""System coverage for W28A-513 requirements and E2E documentation gaps.

Description:
- exercises the real VDB-backed ingestion path with all documented chunking strategies,
- validates a live OCR provider path without mocks,
- verifies the actual retrieval output contract delivered by the runtime.

Related requirements:
- FR-09A
- FR-10A
- FR-14A
- FR-16A
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO

import pytest
from cloud_dog_vdb.ingestion.chunk.base import Chunker
from cloud_dog_vdb.ingestion.chunk.fixed import FixedChunker
from cloud_dog_vdb.ingestion.chunk.recursive import RecursiveChunker
from cloud_dog_vdb.ingestion.chunk.semantic import SemanticChunker
from cloud_dog_vdb.ingestion.convert.base import NoOpConverter
from cloud_dog_vdb.domain.models import Record
from cloud_dog_vdb.ingestion.ocr.providers.local import LocalOCRProvider
from PIL import Image, ImageDraw, ImageFont

from index_tools.pipeline.chunking import paragraph_chunks, token_chunks
from tests.live_runtime import LiveIndexRuntime


@dataclass(frozen=True, slots=True)
class _ChunkingExpectation:
    """Describe the expected chunk output for a strategy."""

    strategy: str
    chunker: Chunker
    text: str
    expected_chunks: list[str]


class _TokenChunker(Chunker):
    """Adapt project token chunking into the delegated chunker protocol."""

    def __init__(self, *, chunk_size: int, chunk_overlap: int) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> list[str]:
        """Split text using the project token-overlap strategy."""
        return token_chunks(text, chunk_size=self._chunk_size, chunk_overlap=self._chunk_overlap)


class _ParagraphChunker(Chunker):
    """Adapt project paragraph chunking into the delegated chunker protocol."""

    def chunk(self, text: str) -> list[str]:
        """Split text using paragraph boundaries."""
        return paragraph_chunks(text)


def _ingest_with_chunker(
    live_service: LiveIndexRuntime,
    *,
    strategy: str,
    provider_id: str,
    text: str,
    chunker: Chunker,
) -> list[str]:
    """Ingest text with a concrete chunker into a real backend collection."""

    profile = "default"
    collection = f"st15_{strategy}"
    collection_name = live_service.ensure_collection(profile, collection, provider_id=provider_id)
    converted = NoOpConverter().convert(text)
    created_at = datetime.now(timezone.utc).isoformat()
    records = [
        Record(
            record_id=f"st15-{strategy}-{index}",
            content=chunk,
            metadata={
                "tenant_id": "default",
                "source_uri": f"ingestion://{collection_name}/st15-{strategy}/{index}",
                "source_type": "other",
                "lifecycle_state": "active",
                "created_at": created_at,
            },
        )
        for index, chunk in enumerate(chunker.chunk(converted))
    ]
    _ = live_service._run(  # noqa: SLF001 - system coverage requires the real delegated ingest path
        live_service.vdb_client.upsert_records(collection_name, records, provider_id=provider_id)
    )
    rows = live_service._run(  # noqa: SLF001 - system coverage requires direct verification against the backend
        live_service.vdb_client.list_records(collection_name, provider_id=provider_id)
    )
    ordered = sorted(rows, key=lambda row: str(row.record_id))
    return [str(row.content) for row in ordered]


def _coverage_provider(live_service: LiveIndexRuntime) -> str:
    """Choose a stable real backend for backend-agnostic coverage assertions."""
    providers = live_service.required_live_providers()
    if "chroma" in providers:
        return "chroma"
    return providers[0]


def _normalise_ocr_text(value: str) -> str:
    """Normalise OCR text for stable assertions."""

    return " ".join(value.lower().split())


def _render_png(text: str) -> bytes:
    """Render a simple OCR fixture image in-memory."""

    image = Image.new("RGB", (900, 220), color="white")
    draw = ImageDraw.Draw(image)
    font = None
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            font = ImageFont.truetype(candidate, 56)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    draw.text((40, 70), text, fill="black", font=font)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.probe  # W28C-1711-R3.5 invalid-binding archived (FR-009)


def test_st_15_chunking_strategies_ingest_expected_boundaries(live_service: LiveIndexRuntime) -> None:
    """Ingest with all documented strategies and verify chunk boundaries."""

    provider_id = _coverage_provider(live_service)
    expectations = [
        _ChunkingExpectation(
            strategy="token_overlap",
            chunker=_TokenChunker(chunk_size=3, chunk_overlap=1),
            text="alpha beta gamma delta epsilon zeta eta",
            expected_chunks=[
                "alpha beta gamma",
                "gamma delta epsilon",
                "epsilon zeta eta",
            ],
        ),
        _ChunkingExpectation(
            strategy="paragraph",
            chunker=_ParagraphChunker(),
            text="Paragraph one.\n\nParagraph two.\n\nParagraph three.",
            expected_chunks=[
                "Paragraph one.",
                "Paragraph two.",
                "Paragraph three.",
            ],
        ),
        _ChunkingExpectation(
            strategy="fixed_size",
            chunker=FixedChunker(size=5),
            text="ABCDEFGHIJKL",
            expected_chunks=["ABCDE", "FGHIJ", "KL"],
        ),
        _ChunkingExpectation(
            strategy="semantic",
            chunker=SemanticChunker(min_sentence_len=20),
            text="Short. This sentence is definitely long enough. Another meaningful sentence appears.",
            expected_chunks=[
                "Short. This sentence is definitely long enough",
                "Another meaningful sentence appears",
            ],
        ),
        _ChunkingExpectation(
            strategy="recursive",
            chunker=RecursiveChunker(max_chars=24),
            text="Heading A\nLine A\n\nHeading B\nLine B",
            expected_chunks=["Heading A\nLine A", "Heading B\nLine B"],
        ),
    ]

    for expectation in expectations:
        chunks = _ingest_with_chunker(
            live_service,
            strategy=expectation.strategy,
            provider_id=provider_id,
            text=expectation.text,
            chunker=expectation.chunker,
        )
        assert chunks == expectation.expected_chunks
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.probe  # W28C-1711-R3.5 invalid-binding archived (FR-009)


def test_st_15_local_ocr_provider_extracts_non_empty_text() -> None:
    """Verify a real local OCR provider can extract readable text."""

    provider = LocalOCRProvider(timeout_seconds=30.0)
    assert asyncio.run(provider.health_check()) is True

    document = _render_png("ALPHA OCR TEST")
    extracted = asyncio.run(
        provider.extract_text(
            document,
            filename="alpha-ocr-test.png",
            mime_type="image/png",
        )
    )
    normalised = _normalise_ocr_text(extracted)
    assert normalised
    assert "alpha" in normalised
    assert "ocr" in normalised
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.probe  # W28C-1711-R3.5 invalid-binding archived (FR-009)


def test_st_15_retrieval_returns_content_and_source_uri_traceability(
    live_service: LiveIndexRuntime,
) -> None:
    """Verify the actual runtime retrieval contract: content plus source URI metadata."""

    provider_id = _coverage_provider(live_service)
    source_uri = "file://system/st15/retrieve-contract.txt"
    record = live_service.ingest_text(
        "default",
        "st15_retrieve_modes",
        "retrieval contract payload for source uri verification",
        source_uri,
        actor="system",
        provider_id=provider_id,
    )

    results = live_service.search(
        "default",
        "st15_retrieve_modes",
        "source uri verification",
        provider_id=provider_id,
        top_k=3,
    )
    assert results
    assert "retrieval contract payload" in str(results[0]["content"])
    assert str((results[0].get("metadata") or {}).get("source_uri", "")) == source_uri

    retrieved = live_service.retrieve("default", "st15_retrieve_modes", record.record_id, provider_id=provider_id)
    assert retrieved is not None
    assert "retrieval contract payload" in str(retrieved.content)
    assert str(retrieved.metadata.get("source_uri", "")) == source_uri
