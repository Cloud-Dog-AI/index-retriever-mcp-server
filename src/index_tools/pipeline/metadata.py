# index-retriever-mcp-server — Metadata Enrichment
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Metadata extraction and enrichment helpers.

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path


def build_metadata(source: str, content: bytes, profile: str, collection: str) -> dict[str, str | int]:
    """Build consistent metadata for ingestion records."""
    timestamp = datetime.now(timezone.utc).isoformat()  # noqa: UP017
    name = Path(source).name or source
    return {
        "source": source,
        "filename": name,
        "size": len(content),
        "content_hash": sha256(content).hexdigest(),
        "ingested_at": timestamp,
        "modified_at": timestamp,
        "profile": profile,
        "collection": collection,
    }
