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

# index-retriever-mcp-server — Ingest Pipeline
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Ingestion orchestration from source to vector upsert.

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(slots=True)
class PipelineResult:
    """PipelineResult definition."""

    doc_id: str
    chunk_count: int
    embedded_count: int


class IngestPipeline:
    """Composable ingestion pipeline for deterministic unit testing."""

    def __init__(
        self,
        fetch_content: Callable[[str], bytes],
        convert_content: Callable[[bytes], str],
        chunk_content: Callable[[str], list[str]],
        embed_chunks: Callable[[list[str]], list[list[float]]],
        upsert_vectors: Callable[[str, list[str], list[list[float]]], None],
    ) -> None:
        """Initialise the instance state."""
        self.fetch_content = fetch_content
        self.convert_content = convert_content
        self.chunk_content = chunk_content
        self.embed_chunks = embed_chunks
        self.upsert_vectors = upsert_vectors

    def run(self, source: str, doc_id: str) -> tuple[PipelineResult, list[str]]:
        """Execute run."""
        progress: list[str] = []

        raw = self.fetch_content(source)
        progress.append("fetched")

        text = self.convert_content(raw)
        progress.append("converted")

        chunks = self.chunk_content(text)
        progress.append("chunked")

        vectors = self.embed_chunks(chunks)
        progress.append("embedded")

        self.upsert_vectors(doc_id, chunks, vectors)
        progress.append("upserted")

        return PipelineResult(doc_id=doc_id, chunk_count=len(chunks), embedded_count=len(vectors)), progress
