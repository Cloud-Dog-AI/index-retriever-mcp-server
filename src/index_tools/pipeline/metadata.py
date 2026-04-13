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

from __future__ import annotations

from typing import Any
import mimetypes
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

from cloud_dog_vdb.metadata.identity import (
    compute_content_hash,
    compute_doc_id,
    compute_record_id,
    normalise_source_uri,
)
from cloud_dog_vdb.metadata.schema import validate_metadata
from cloud_dog_storage import path_utils


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")  # noqa: UP017


def _resolve_filename(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    candidate = parsed.path if parsed.scheme else source_uri
    return path_utils.name(unquote(candidate)) or source_uri


def _resolve_mime_type(source_uri: str, filename: str) -> str:
    preferred = filename or _resolve_filename(source_uri)
    guessed, _ = mimetypes.guess_type(preferred)
    return guessed or "text/plain"


def _resolve_source_type(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    scheme = parsed.scheme.strip().lower()
    if not scheme or scheme == "file":
        return "file"
    if scheme in {"http", "https"}:
        return "web"
    if scheme in {"postgres", "postgresql", "mysql", "sqlite", "mssql"}:
        return "database"
    if scheme in {"api"}:
        return "api"
    return "other"


def build_metadata(source: str, content: bytes, profile: str, collection: str) -> dict[str, Any]:
    """Build consistent metadata for ingestion records."""
    # Covers: FR-10, FR-14
    source_uri = normalise_source_uri(source)
    content_text = content.decode("utf-8", errors="replace")
    content_hash = compute_content_hash(content_text)
    doc_id = compute_doc_id(source_uri, content_hash)
    record_id = compute_record_id(doc_id, 0)
    timestamp = _utc_timestamp()
    filename = _resolve_filename(source_uri)
    mime_type = _resolve_mime_type(source_uri, filename)
    metadata: dict[str, Any] = {
        "doc_id": doc_id,
        "record_id": record_id,
        "chunk_id": record_id,
        "chunk_index": 0,
        "is_latest": True,
        "tenant_id": profile,
        "namespace": f"{profile}:{collection}",
        "source": source_uri,
        "source_uri": source_uri,
        "source_type": _resolve_source_type(source_uri),
        "filename": filename,
        "mime_type": mime_type,
        "size": len(content),
        "size_bytes": len(content),
        "content_hash": content_hash,
        "source_hash": compute_content_hash(source_uri),
        "created_at": timestamp,
        "ingested_at": timestamp,
        "modified_at": timestamp,
        "lifecycle_state": "active",
        "app_id": "index-retriever",
        "user_id": "",
        "session_id": "",
        "profile": profile,
        "collection": collection,
        "embedding_model": "",
        "chunker": "token_chunks",
        "chunker_version": "v1",
        "token_count": len(content_text.split()),
        "access_tags": [],
        "parser_name": "internal",
        "parser_version": "",
        "parser_provider": "internal",
        "ocr_provider": "",
        "ocr_engine": "",
        "ocr_confidence": None,
        "ocr_applied": False,
        "page": None,
        "page_number": None,
        "page_range": "",
        "section": "",
        "section_path": "",
        "table_id": "",
        "table_title": "",
        "chunk_kind": "document",
        "extras": {},
    }
    errors = validate_metadata(metadata)
    if errors:
        raise ValueError(f"Invalid canonical metadata: {'; '.join(errors)}")
    return metadata
