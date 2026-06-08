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

"""ORM tables for canonical document structure (design brief §6, §7.1).

Persisted through ``cloud_dog_db`` (``PlatformBase`` + ``TimestampMixin``) exactly like the
existing :class:`~index_tools.db.models.IndexPlatformDbState`. Each row carries first-class
identity/link/order columns for filtering and a ``payload`` JSON column holding the full
canonical object — §3 explicitly permits JSON behind the common SQL interface, and the
generic :class:`sqlalchemy.JSON` type round-trips across the sqlite/postgresql/mysql backends
the existing matrix supports.
"""

from __future__ import annotations

from typing import Any

from cloud_dog_db import PlatformBase, TimestampMixin
from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class StructureDocumentRow(PlatformBase, TimestampMixin):
    """Canonical structure record for one source document (design brief §6.1)."""

    __tablename__ = "structure_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    structure_document_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    profile_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    collection_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_document_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    file_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="", index=True)
    extractor_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="complete", index=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StructurePageRow(PlatformBase, TimestampMixin):
    """Page-level layout (design brief §6.2)."""

    __tablename__ = "structure_pages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    page_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    structure_document_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StructureBlockRow(PlatformBase, TimestampMixin):
    """Atomic layout/content object (design brief §6.3)."""

    __tablename__ = "structure_blocks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    block_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    structure_document_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    page_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    section_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    block_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    reading_order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StructureSectionRow(PlatformBase, TimestampMixin):
    """Logical section hierarchy (design brief §6.4)."""

    __tablename__ = "structure_sections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    section_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    structure_document_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parent_section_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StructureStyleRow(PlatformBase, TimestampMixin):
    """Normalised style class (design brief §6.5)."""

    __tablename__ = "structure_styles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    style_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    structure_document_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    style_class: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StructureTableRow(PlatformBase, TimestampMixin):
    """Table metadata (design brief §6.6)."""

    __tablename__ = "structure_tables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    structure_document_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    page_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StructureFigureRow(PlatformBase, TimestampMixin):
    """Figure/image metadata (design brief §6.7)."""

    __tablename__ = "structure_figures"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    figure_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    structure_document_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    page_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StructureRelationRow(PlatformBase, TimestampMixin):
    """Structure relation edge (design brief §6.8)."""

    __tablename__ = "structure_relations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    relation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    structure_document_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    source_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    target_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StructureExtractorRunRow(PlatformBase, TimestampMixin):
    """Parser/provider run metadata (design brief §5.2, §8.3)."""

    __tablename__ = "structure_extractor_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    extractor_run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    structure_document_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="complete")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


#: Child row classes keyed by their structure-bundle field name (used by the repository).
CHILD_ROW_TYPES: dict[str, type[PlatformBase]] = {
    "pages": StructurePageRow,
    "blocks": StructureBlockRow,
    "sections": StructureSectionRow,
    "styles": StructureStyleRow,
    "tables": StructureTableRow,
    "figures": StructureFigureRow,
    "relations": StructureRelationRow,
    "extractor_runs": StructureExtractorRunRow,
}

__all__ = [
    "StructureDocumentRow",
    "StructurePageRow",
    "StructureBlockRow",
    "StructureSectionRow",
    "StructureStyleRow",
    "StructureTableRow",
    "StructureFigureRow",
    "StructureRelationRow",
    "StructureExtractorRunRow",
    "CHILD_ROW_TYPES",
]
