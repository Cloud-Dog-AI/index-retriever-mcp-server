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

"""Structure extraction: parser output -> canonical StructureBundle (design brief §9, §25 #2/#3).

The `internal` provider is a pure-Python, offline-deterministic normaliser (markdown-aware) used as the
default and in tests. The mineru/marker/docling providers reuse the existing cloud_dog_vdb parser registry
(`build_parser_registry` + `parse_bytes`) and normalise the returned intermediate representation (IR).
"""

from __future__ import annotations

import re
from hashlib import sha256
from typing import Any

from index_tools.structure.models import (
    BlockType,
    SectionType,
    StructureBlock,
    StructureBundle,
    StructureDocument,
    StructureExtractorRun,
    StructurePage,
    StructureSection,
    StructureStyle,
    StructureTable,
)

#: Providers represented through the structure extractor (design brief §9.1). `internal` is offline.
SUPPORTED_PROVIDERS = ("internal", "mineru", "marker_mcp", "docling")

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_MD_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_SECTION_KEYWORDS = {
    "introduction": SectionType.introduction,
    "scope": SectionType.scope,
    "method": SectionType.methodology,
    "methodology": SectionType.methodology,
    "findings": SectionType.findings,
    "analysis": SectionType.analysis,
    "risk": SectionType.risk,
    "recommendation": SectionType.recommendations,
    "recommendations": SectionType.recommendations,
    "implementation": SectionType.implementation,
    "appendix": SectionType.appendix,
    "references": SectionType.references,
    "glossary": SectionType.glossary,
    "summary": SectionType.executive_summary,
    "executive summary": SectionType.executive_summary,
}


def _classify_section(title: str) -> SectionType:
    low = title.strip().lower()
    for key, value in _SECTION_KEYWORDS.items():
        if key in low:
            return value
    return SectionType.unknown


def normalise_text_to_bundle(
    text: str,
    *,
    profile: str,
    collection: str,
    source_uri: str | None = None,
    source_filename: str | None = None,
    provider: str = "internal",
    extractor_version: str = "1.0",
) -> StructureBundle:
    """Markdown-aware deterministic normalisation of plain text into a canonical bundle."""
    source_hash = sha256((text or "").encode("utf-8")).hexdigest()
    document = StructureDocument(
        profile_id=profile,
        collection_id=collection,
        source_uri=source_uri,
        source_filename=source_filename,
        source_hash=source_hash,
        source_size=len(text.encode("utf-8")),
        extractor_provider=provider,
        extractor_version=extractor_version,
        page_count=1,
    )
    page = StructurePage(page_number=1)
    blocks: list[StructureBlock] = []
    sections: list[StructureSection] = []
    tables: list[StructureTable] = []
    styles: list[StructureStyle] = []
    seen_styles: set[str] = set()

    order = 0
    current_section: StructureSection | None = None
    table_buffer: list[str] = []

    def _flush_table() -> None:
        nonlocal order
        if len(table_buffer) >= 2:
            rows = [[c.strip() for c in row.strip().strip("|").split("|")] for row in table_buffer]
            header_rows = 1 if rows and all("---" not in c for c in rows[0]) else 0
            tables.append(
                StructureTable(
                    structure_document_id="",
                    page_id="",
                    section_id=current_section.section_id if current_section else None,
                    row_count=len(rows),
                    column_count=max((len(r) for r in rows), default=0),
                    header_rows=header_rows,
                    cells=[{"row": i, "cells": r} for i, r in enumerate(rows)],
                    normalised_markdown="\n".join(table_buffer),
                    extraction_method=provider,
                )
            )
            blocks.append(
                StructureBlock(
                    page_id="",
                    section_id=current_section.section_id if current_section else None,
                    block_type=BlockType.table,
                    text="\n".join(table_buffer),
                    reading_order_index=order,
                )
            )
            order += 1
        table_buffer.clear()

    paragraphs = re.split(r"\n\s*\n", text.strip()) if text.strip() else []
    for para in paragraphs:
        for raw_line in para.splitlines():
            if _MD_TABLE_ROW_RE.match(raw_line):
                table_buffer.append(raw_line)
                continue
            if table_buffer:
                _flush_table()
        if table_buffer:
            _flush_table()

        stripped = para.strip()
        if not stripped or all(_MD_TABLE_ROW_RE.match(line) for line in stripped.splitlines()):
            continue

        heading = _HEADING_RE.match(stripped.splitlines()[0]) if stripped else None
        if heading:
            level = len(heading.group(1)) - 1
            title = heading.group(2).strip()
            section = StructureSection(
                structure_document_id="",
                level=level,
                title=title,
                normalised_title=title.lower(),
                section_type=_classify_section(title),
                start_page=1,
            )
            sections.append(section)
            current_section = section
            blocks.append(
                StructureBlock(
                    page_id="",
                    section_id=section.section_id,
                    block_type=BlockType.heading if level > 0 else BlockType.title,
                    text=title,
                    reading_order_index=order,
                    style_id=None,
                )
            )
            order += 1
            style_class = f"heading_{level}"
            if style_class not in seen_styles:
                seen_styles.add(style_class)
                styles.append(StructureStyle(structure_document_id="", style_class=style_class, style_role="heading", observed_count=1))
            continue

        blocks.append(
            StructureBlock(
                page_id="",
                section_id=current_section.section_id if current_section else None,
                block_type=BlockType.paragraph,
                text=stripped,
                reading_order_index=order,
            )
        )
        order += 1
        if "body" not in seen_styles:
            seen_styles.add("body")
            styles.append(StructureStyle(structure_document_id="", style_class="body", style_role="body", observed_count=1))

    if table_buffer:
        _flush_table()

    run = StructureExtractorRun(provider=provider, version=extractor_version, config={"mode": "internal"})
    return StructureBundle(
        document=document,
        pages=[page],
        blocks=blocks,
        sections=sections,
        styles=styles,
        tables=tables,
        extractor_runs=[run],
    )


def normalise_ir_to_bundle(
    ir: Any,
    *,
    profile: str,
    collection: str,
    source_uri: str | None = None,
    source_filename: str | None = None,
    provider: str = "internal",
) -> StructureBundle:
    """Normalise a cloud_dog_vdb parser intermediate representation (IR) into a canonical bundle."""
    full_text = ir.full_text() if hasattr(ir, "full_text") else str(ir)
    provider_id = str(getattr(ir, "provider_id", provider) or provider)
    version = str(getattr(ir, "provider_version", "") or "")
    bundle = normalise_text_to_bundle(
        full_text,
        profile=profile,
        collection=collection,
        source_uri=source_uri or str(getattr(ir, "source_uri", "") or "") or None,
        source_filename=source_filename,
        provider=provider_id,
        extractor_version=version or "1.0",
    )
    # carry parser-reported tables/quality where present
    quality = dict(getattr(ir, "quality", {}) or {})
    if quality:
        bundle.document.quality_score = float(quality.get("score", quality.get("quality_score", 0)) or 0) or bundle.document.quality_score
        bundle.document.metadata["parser_quality"] = quality
    table_blocks = list(getattr(ir, "table_blocks", []) or [])
    for index, tb in enumerate(table_blocks):
        bundle.tables.append(
            StructureTable(
                structure_document_id="",
                normalised_markdown=str(getattr(tb, "markdown", getattr(tb, "text", "")) or ""),
                extraction_method=provider_id,
                metadata={"source_index": index},
            )
        )
    bundle.extractor_runs = [
        StructureExtractorRun(provider=provider_id, version=version or "1.0", config={"mode": "vdb"}, metadata={"quality": quality})
    ]
    return bundle


class StructureExtractor:
    """Extract canonical structure from text or bytes and persist via the Phase-1 service."""

    def __init__(self, service: Any) -> None:
        """Bind the StructureService used to persist + audit extracted bundles."""
        self.service = service

    def extract_text(
        self,
        text: str,
        *,
        profile: str,
        collection: str,
        source_uri: str | None = None,
        source_filename: str | None = None,
        provider: str = "internal",
        actor: str = "service",
        roles: set[str] | None = None,
    ) -> dict[str, Any]:
        """Extract structure from inline text (offline, deterministic) and persist it."""
        bundle = normalise_text_to_bundle(
            text,
            profile=profile,
            collection=collection,
            source_uri=source_uri,
            source_filename=source_filename,
            provider=provider,
        )
        return self.service.create(bundle, actor=actor, roles=roles)

    def extract_bytes(
        self,
        data: bytes,
        *,
        filename: str,
        mime_type: str = "application/octet-stream",
        profile: str,
        collection: str,
        provider: str = "internal",
        parser_services: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        actor: str = "service",
        roles: set[str] | None = None,
    ) -> dict[str, Any]:
        """Extract structure from document bytes.

        provider=`internal` decodes as text (offline). mineru/marker/docling delegate to the existing
        cloud_dog_vdb parser registry and normalise the returned IR.
        """
        if provider == "internal":
            return self.extract_text(
                data.decode("utf-8", errors="replace"),
                profile=profile,
                collection=collection,
                source_filename=filename,
                provider="internal",
                actor=actor,
                roles=roles,
            )
        ir = _parse_via_vdb(data, filename=filename, mime_type=mime_type, provider=provider, parser_services=parser_services, options=options)
        bundle = normalise_ir_to_bundle(ir, profile=profile, collection=collection, source_filename=filename, provider=provider)
        return self.service.create(bundle, actor=actor, roles=roles)


def _parse_via_vdb(data: bytes, *, filename: str, mime_type: str, provider: str, parser_services: dict[str, Any] | None, options: dict[str, Any] | None) -> Any:
    """Parse bytes through the existing cloud_dog_vdb parser registry for a named provider."""
    import asyncio

    from cloud_dog_vdb.ingestion.parsers import build_parser_registry  # type: ignore

    registry = build_parser_registry(parser_services or {})
    parser = registry.get(provider)
    if parser is None:
        raise ValueError(f"parser provider not available: {provider}")

    async def _run() -> Any:
        return await parser.parse_bytes(data, filename=filename, source_uri=filename, mime_type=mime_type, options=options or {})

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run())
    raise RuntimeError("extract_bytes for live providers must be called outside a running event loop")
