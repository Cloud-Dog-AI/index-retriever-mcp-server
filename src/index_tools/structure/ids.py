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

"""Deterministic identity helpers for canonical document structure (design brief §8.2).

Stable IDs let the same source document re-extract to the same structure IDs, which is
what versioning/reprocessing (§8.4) and VDB linkage (§8.1) depend on. The scheme is a
single sha256-based standard owned here so IndexRetriever does not create an
incompatible local identity scheme (§8.2 closing requirement).
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

_FIELD_SEP = "\x1f"  # unit separator — unambiguous component boundary


def _digest(prefix: str, *parts: Any) -> str:
    """Return ``<prefix>_<hex>`` where hex is sha256 over the canonical part tuple."""
    joined = _FIELD_SEP.join("" if part is None else str(part) for part in parts)
    return f"{prefix}_{sha256(joined.encode('utf-8')).hexdigest()}"


def text_hash(text: str | None) -> str:
    """Stable hash of (possibly large) text content, used as an ID component."""
    return sha256((text or "").encode("utf-8")).hexdigest()


def normalise_bbox(bbox: Any) -> str:
    """Canonical string form of a bounding box for ID stability."""
    if bbox is None:
        return ""
    if isinstance(bbox, (list, tuple)):
        return ",".join(f"{float(value):.3f}" for value in bbox)
    return str(bbox)


def structure_document_id(
    *,
    profile_id: str,
    collection_id: str,
    source_hash: str,
    parser_family: str,
    schema_version: str,
) -> str:
    """``hash(profile_id, collection_id, source_hash, parser_family, schema_version)`` (§8.2)."""
    return _digest("sd", profile_id, collection_id, source_hash, parser_family, schema_version)


def page_id(structure_document_id: str, page_number: int | str) -> str:
    """``hash(structure_document_id, page_number)`` (§8.2)."""
    return _digest("pg", structure_document_id, page_number)


def block_id(
    *,
    page_id: str,
    reading_order_index: int | str,
    bbox: Any,
    text: str | None,
    block_type: str,
) -> str:
    """``hash(page_id, reading_order_index, bbox, text_hash, block_type)`` (§8.2)."""
    return _digest("bk", page_id, reading_order_index, normalise_bbox(bbox), text_hash(text), block_type)


def section_id(
    *,
    structure_document_id: str,
    normalised_path: str,
    start_page: int | str,
    title: str | None,
) -> str:
    """``hash(structure_document_id, normalised_path, start_page, title_hash)`` (§8.2)."""
    return _digest("se", structure_document_id, normalised_path, start_page, text_hash(title))
