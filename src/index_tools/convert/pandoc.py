# index-retriever-mcp-server — Pandoc Converter
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Optional converter using Pandoc when available.

from __future__ import annotations


def convert(content: bytes) -> str:
    """Convert document bytes to text via best-effort UTF-8 decode fallback."""
    return content.decode("utf-8", errors="replace")
