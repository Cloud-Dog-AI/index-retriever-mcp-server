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

# index-retriever-mcp-server — Chunking
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Chunk generation strategies for ingest pipeline.

from __future__ import annotations


def token_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text by whitespace token count with overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between 0 and chunk_size-1")

    tokens = text.split()
    if not tokens:
        return []

    chunks: list[str] = []
    step = chunk_size - chunk_overlap
    for start in range(0, len(tokens), step):
        part = tokens[start : start + chunk_size]
        if not part:
            break
        chunks.append(" ".join(part))
        if start + chunk_size >= len(tokens):
            break
    return chunks


def paragraph_chunks(text: str) -> list[str]:
    """Split text by blank lines."""
    return [section.strip() for section in text.split("\n\n") if section.strip()]
