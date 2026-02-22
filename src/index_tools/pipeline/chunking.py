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
