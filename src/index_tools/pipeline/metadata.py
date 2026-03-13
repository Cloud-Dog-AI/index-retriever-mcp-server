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
