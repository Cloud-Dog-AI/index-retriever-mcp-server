# index-retriever-mcp-server — Office Converter
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Office document conversion helper.

from __future__ import annotations


def extract_text(content: bytes) -> str:
    """Extract text from Office document bytes using decode fallback."""
    return content.decode("utf-8", errors="replace")
