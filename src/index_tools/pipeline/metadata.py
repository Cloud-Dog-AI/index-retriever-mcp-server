# index-retriever-mcp-server — Metadata Enrichment
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Metadata extraction and enrichment helpers.

from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import unquote, urlparse


def _resolve_filename(source: str) -> str:
    parsed = urlparse(source)
    candidate = parsed.path if parsed.scheme else source
    return Path(unquote(candidate)).name or source


def _resolve_mime_type(source: str, filename: str) -> str:
    preferred = filename or _resolve_filename(source)
    guessed, _ = mimetypes.guess_type(preferred)
    return guessed or "text/plain"


def build_metadata(source: str, content: bytes, profile: str, collection: str) -> dict[str, str | int]:
    """Build consistent metadata for ingestion records."""
    timestamp = datetime.now(timezone.utc).isoformat()  # noqa: UP017
    name = _resolve_filename(source)
    mime_type = _resolve_mime_type(source, name)
    return {
        "source": source,
        "source_uri": source,
        "filename": name,
        "mime_type": mime_type,
        "size": len(content),
        "content_hash": sha256(content).hexdigest(),
        "ingested_at": timestamp,
        "modified_at": timestamp,
        "profile": profile,
        "collection": collection,
    }
