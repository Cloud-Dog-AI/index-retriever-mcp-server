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
    if parsed.scheme:
        candidate = parsed.path or parsed.netloc
    else:
        candidate = source_uri
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


def build_metadata(
    source: str,
    content: bytes,
    profile: str,
    collection: str,
    caller_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build consistent metadata for ingestion records.

    When *caller_metadata* contains a ``mime_type`` key, that value is
    used instead of the heuristic resolved from *source*.  This lets the
    upload handler supply the correct MIME type inferred from the original
    filename even when the ``upload://`` URI scheme would confuse
    ``mimetypes.guess_type``.
    """
    # Covers: FR-10, FR-14
    source_uri = normalise_source_uri(source)
    content_text = content.decode("utf-8", errors="replace")
    content_hash = compute_content_hash(content_text)
    doc_id = compute_doc_id(source_uri, content_hash)
    record_id = compute_record_id(doc_id, 0)
    timestamp = _utc_timestamp()
    filename = _resolve_filename(source_uri)
    caller = caller_metadata if isinstance(caller_metadata, dict) else {}
    mime_type = str(caller.get("mime_type", "")).strip() or _resolve_mime_type(source_uri, filename)
    metadata: dict[str, Any] = {
        "doc_id": doc_id,
        "document_id": doc_id,
        "record_id": record_id,
        "index_record_id": record_id,
        "chunk_id": record_id,
        "chunk_index": 0,
        "is_latest": True,
        "tenant_id": profile,
        "dataset_id": str(caller.get("dataset_id", "")).strip() or profile,
        "collection_id": collection,
        "namespace": f"{profile}:{collection}",
        "source": source_uri,
        "source_uri": source_uri,
        "source_type": _resolve_source_type(source_uri),
        "filename": filename,
        "title": str(caller.get("title", "")).strip() or filename,
        "mime_type": mime_type,
        "language": str(caller.get("language", "")).strip() or "und",
        "size": len(content),
        "size_bytes": len(content),
        "content_hash": content_hash,
        "source_hash": compute_content_hash(source_uri),
        "created_at": timestamp,
        "updated_at": str(caller.get("updated_at", "")).strip() or timestamp,
        "ingested_at": timestamp,
        "modified_at": timestamp,
        "lifecycle_state": "active",
        "status": "active",
        "authoritative_source": bool(caller.get("authoritative_source", False)),
        "app_id": "index-retriever",
        "user_id": "",
        "session_id": "",
        "profile": profile,
        "collection": collection,
        "embedding_model": "",
        "embedding_dimensions": None,
        "embedding_version": "",
        "chunker": "token_chunks",
        "chunking_strategy": "token_chunks",
        "chunker_version": "v1",
        "pipeline_version": "v1",
        "normalisation_version": "v1",
        "index_version": "v1",
        "index_family": "index-retriever",
        "visibility": str(caller.get("visibility", "")).strip() or "tenant",
        "access_scope": str(caller.get("access_scope", "")).strip() or profile,
        "retention_class": caller.get("retention_class"),
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
