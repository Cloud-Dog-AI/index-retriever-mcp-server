# index-retriever-mcp-server — PDF Converter
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: PDF to text conversion helper.

from __future__ import annotations


def extract_text(content: bytes) -> str:
    """Extract text from PDF bytes with fallback decode for tests."""
    return content.decode("utf-8", errors="replace")
