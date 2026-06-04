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

"""Canonical document-structure model (design brief §5.2, §6.1-6.8).

Transport-neutral pydantic models. Parser-specific output is preserved only as
provenance/extension data (``metadata`` / ``source_parser_payload_ref``); the public
API contracts use this canonical model regardless of which parser produced it (§6 intro).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

#: Canonical structure schema version (design brief §6.1 ``schema_version`` / §8.4).
SCHEMA_VERSION = "1.0"


class BlockType(str, Enum):
    """Required block types (design brief §6.3)."""

    title = "title"
    heading = "heading"
    paragraph = "paragraph"
    list = "list"
    list_item = "list_item"
    table = "table"
    table_cell = "table_cell"
    figure = "figure"
    caption = "caption"
    header = "header"
    footer = "footer"
    footnote = "footnote"
    callout = "callout"
    quote = "quote"
    code = "code"
    formula = "formula"
    page_number = "page_number"
    separator = "separator"
    unknown = "unknown"


class SectionType(str, Enum):
    """Section type examples (design brief §6.4)."""

    front_matter = "front_matter"
    cover = "cover"
    document_control = "document_control"
    executive_summary = "executive_summary"
    introduction = "introduction"
    scope = "scope"
    methodology = "methodology"
    findings = "findings"
    analysis = "analysis"
    risk = "risk"
    recommendations = "recommendations"
    implementation = "implementation"
    appendix = "appendix"
    references = "references"
    glossary = "glossary"
    unknown = "unknown"


class StructureStatus(str, Enum):
    """Explicit structure status values (design brief §8.4)."""

    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"
    partial = "partial"
    stale = "stale"
    superseded = "superseded"


class StructureDocument(BaseModel):
    """Canonical structure record for one source document (design brief §6.1)."""

    structure_document_id: str = ""
    source_document_id: str | None = None
    file_id: str | None = None
    profile_id: str
    collection_id: str
    tenant_id: str | None = None
    source_uri: str | None = None
    source_filename: str | None = None
    source_mime_type: str | None = None
    source_hash: str = ""
    source_size: int | None = None
    source_created_at: str | None = None
    source_modified_at: str | None = None
    ingest_job_id: str | None = None
    structure_job_id: str | None = None
    extractor_provider: str = "manual"
    extractor_version: str = ""
    extractor_config_hash: str = ""
    schema_version: str = SCHEMA_VERSION
    language_hints: list[str] = Field(default_factory=list)
    page_count: int = 0
    quality_score: float | None = None
    status: StructureStatus = StructureStatus.complete
    created_by: str | None = None
    visibility: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructurePage(BaseModel):
    """Page-level layout (design brief §6.2)."""

    page_id: str = ""
    structure_document_id: str = ""
    page_number: int
    width: float | None = None
    height: float | None = None
    unit: str | None = None
    rotation: float | None = None
    layout_type: str | None = None
    reading_order_block_ids: list[str] = Field(default_factory=list)
    zones: list[dict[str, Any]] = Field(default_factory=list)
    headers: list[str] = Field(default_factory=list)
    footers: list[str] = Field(default_factory=list)
    marginalia: list[str] = Field(default_factory=list)
    page_image_ref: str | None = None
    thumbnail_ref: str | None = None
    quality_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructureBlock(BaseModel):
    """Atomic layout/content object (design brief §6.3)."""

    block_id: str = ""
    structure_document_id: str = ""
    page_id: str = ""
    section_id: str | None = None
    block_type: BlockType = BlockType.unknown
    subtype: str | None = None
    text: str = ""
    normalised_text: str | None = None
    bbox: list[float] | None = None
    polygon: list[list[float]] | None = None
    reading_order_index: int = 0
    style_id: str | None = None
    confidence: float | None = None
    language: str | None = None
    source_parser_block_id: str | None = None
    source_parser_payload_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructureSection(BaseModel):
    """Logical section hierarchy independent of page layout (design brief §6.4)."""

    section_id: str = ""
    structure_document_id: str = ""
    parent_section_id: str | None = None
    level: int = 0
    title: str | None = None
    normalised_title: str | None = None
    numbering_label: str | None = None
    numbering_scheme: str | None = None
    start_page: int | None = None
    end_page: int | None = None
    start_block_id: str | None = None
    end_block_id: str | None = None
    section_type: SectionType = SectionType.unknown
    summary: str | None = None
    child_section_ids: list[str] = Field(default_factory=list)
    block_ids: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructureStyle(BaseModel):
    """Normalised style class (design brief §6.5)."""

    style_id: str = ""
    structure_document_id: str = ""
    style_class: str
    style_role: str | None = None
    font_family: str | None = None
    font_size: float | None = None
    font_weight: str | None = None
    italic: bool | None = None
    underline: bool | None = None
    colour: str | None = None
    background_colour: str | None = None
    alignment: str | None = None
    line_spacing: float | None = None
    indentation: float | None = None
    spacing_before: float | None = None
    spacing_after: float | None = None
    numbering_pattern: str | None = None
    observed_count: int = 0
    examples: list[str] = Field(default_factory=list)
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructureTable(BaseModel):
    """Table metadata (design brief §6.6)."""

    table_id: str = ""
    structure_document_id: str = ""
    page_id: str | None = None
    section_id: str | None = None
    block_id: str | None = None
    title: str | None = None
    caption: str | None = None
    bbox: list[float] | None = None
    row_count: int = 0
    column_count: int = 0
    header_rows: int = 0
    header_columns: int = 0
    cells: list[dict[str, Any]] = Field(default_factory=list)
    normalised_markdown: str | None = None
    normalised_csv_ref: str | None = None
    quality_score: float | None = None
    extraction_method: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructureFigure(BaseModel):
    """Figure/image metadata (design brief §6.7)."""

    figure_id: str = ""
    structure_document_id: str = ""
    page_id: str | None = None
    section_id: str | None = None
    block_id: str | None = None
    caption: str | None = None
    bbox: list[float] | None = None
    image_ref: str | None = None
    thumbnail_ref: str | None = None
    alt_text: str | None = None
    detected_type: str | None = None
    quality_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructureRelation(BaseModel):
    """Parent/child / contains / references / derived-from edge (design brief §6.8)."""

    relation_id: str = ""
    structure_document_id: str = ""
    relation_type: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    ordering: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructureExtractorRun(BaseModel):
    """Parser/provider run metadata, versions, quality, diagnostics (design brief §5.2, §8.3)."""

    extractor_run_id: str = ""
    structure_document_id: str = ""
    provider: str = "manual"
    version: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    config_hash: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    status: StructureStatus = StructureStatus.complete
    quality_score: float | None = None
    diagnostics: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructureBundle(BaseModel):
    """A structure document together with its child objects.

    Used as the create input and the (optionally child-included) get output so the
    canonical model round-trips exactly through persistence (design brief §6.8 'exact
    reconstruction').
    """

    document: StructureDocument
    pages: list[StructurePage] = Field(default_factory=list)
    blocks: list[StructureBlock] = Field(default_factory=list)
    sections: list[StructureSection] = Field(default_factory=list)
    styles: list[StructureStyle] = Field(default_factory=list)
    tables: list[StructureTable] = Field(default_factory=list)
    figures: list[StructureFigure] = Field(default_factory=list)
    relations: list[StructureRelation] = Field(default_factory=list)
    extractor_runs: list[StructureExtractorRun] = Field(default_factory=list)
