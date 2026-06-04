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

"""Transport-neutral document-structure service (design brief §22, §23).

All API/MCP/A2A/WebUI surfaces route into this single service layer. It owns deterministic
ID assignment (§8.2), persistence through :class:`StructureRepository`, and audit emission
for create/delete (§17, acceptance §25.14). It raises plain ``ValueError``/``KeyError`` for
the transport adapters to translate, exactly like :class:`IndexService`.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from index_tools.structure import ids
from index_tools.structure.models import (
    SCHEMA_VERSION,
    StructureBundle,
    StructureDocument,
    StructureSection,
)
from index_tools.structure.repository import StructureRepository

_CHILD_FIELDS = ("pages", "blocks", "sections", "styles", "tables", "figures", "relations", "extractor_runs")


class StructureService:
    """Business logic for canonical document structure (Phase 1: model + persistence)."""

    def __init__(self, *, repository: StructureRepository | None = None, audit_logger: Any | None = None) -> None:
        """Bind a repository (defaults to the platform-runtime-backed one) and optional audit logger."""
        self.repository = repository or StructureRepository()
        self.audit_logger = audit_logger

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _coerce_bundle(data: StructureBundle | dict[str, Any]) -> StructureBundle:
        if isinstance(data, StructureBundle):
            return data.model_copy(deep=True)
        if "document" in data:
            return StructureBundle.model_validate(data)
        # Accept a bare document payload for the simplest create path.
        return StructureBundle(document=StructureDocument.model_validate(data))

    def _assign_ids(self, bundle: StructureBundle) -> StructureBundle:
        doc = bundle.document
        if not doc.schema_version:
            doc.schema_version = SCHEMA_VERSION
        if not doc.structure_document_id:
            if doc.source_hash:
                doc.structure_document_id = ids.structure_document_id(
                    profile_id=doc.profile_id,
                    collection_id=doc.collection_id,
                    source_hash=doc.source_hash,
                    parser_family=doc.extractor_provider or "manual",
                    schema_version=doc.schema_version,
                )
            else:
                doc.structure_document_id = f"sd_{uuid4().hex}"
        sdid = doc.structure_document_id
        if not doc.page_count and bundle.pages:
            doc.page_count = len(bundle.pages)

        for page in bundle.pages:
            page.structure_document_id = sdid
            if not page.page_id:
                page.page_id = ids.page_id(sdid, page.page_number)
        for block in bundle.blocks:
            block.structure_document_id = sdid
            if not block.block_id:
                block.block_id = ids.block_id(
                    page_id=block.page_id or sdid,
                    reading_order_index=block.reading_order_index,
                    bbox=block.bbox,
                    text=block.text,
                    block_type=str(block.block_type.value if hasattr(block.block_type, "value") else block.block_type),
                )
        for section in bundle.sections:
            section.structure_document_id = sdid
            if not section.section_id:
                normalised_path = section.numbering_label or section.normalised_title or section.title or ""
                section.section_id = ids.section_id(
                    structure_document_id=sdid,
                    normalised_path=normalised_path,
                    start_page=section.start_page if section.start_page is not None else 0,
                    title=section.title,
                )
        for style in bundle.styles:
            style.structure_document_id = sdid
            if not style.style_id:
                style.style_id = f"sty_{uuid4().hex}"
        for table in bundle.tables:
            table.structure_document_id = sdid
            if not table.table_id:
                table.table_id = f"tb_{uuid4().hex}"
        for figure in bundle.figures:
            figure.structure_document_id = sdid
            if not figure.figure_id:
                figure.figure_id = f"fg_{uuid4().hex}"
        for relation in bundle.relations:
            relation.structure_document_id = sdid
            if not relation.relation_id:
                relation.relation_id = f"rel_{uuid4().hex}"
        for run in bundle.extractor_runs:
            run.structure_document_id = sdid
            if not run.extractor_run_id:
                run.extractor_run_id = f"run_{uuid4().hex}"
        return bundle

    def _audit(self, *, actor: str, roles: set[str] | None, action: str, sdid: str, **details: Any) -> None:
        logger = self.audit_logger
        if logger is None:
            return
        log_admin_action = getattr(logger, "log_admin_action", None)
        if not callable(log_admin_action):
            return
        log_admin_action(
            actor=actor,
            roles=set(roles or set()),
            action=action,
            target_type="structure_document",
            target_id=sdid,
            target_name=sdid,
            **details,
        )

    # -- operations ------------------------------------------------------------

    def create(
        self,
        data: StructureBundle | dict[str, Any],
        *,
        actor: str = "service",
        roles: set[str] | None = None,
    ) -> dict[str, Any]:
        """Create (or idempotently replace) a canonical structure document. Returns the stored bundle."""
        bundle = self._assign_ids(self._coerce_bundle(data))
        if not bundle.document.profile_id or not bundle.document.collection_id:
            raise ValueError("structure document requires profile_id and collection_id")
        stored = self.repository.create_bundle(bundle)
        self._audit(
            actor=actor,
            roles=roles,
            action="create",
            sdid=stored.document.structure_document_id,
            new_value={
                "profile_id": stored.document.profile_id,
                "collection_id": stored.document.collection_id,
                "page_count": stored.document.page_count,
                "extractor_provider": stored.document.extractor_provider,
            },
        )
        return stored.model_dump(mode="json")

    def get_document(self, structure_document_id: str) -> dict[str, Any]:
        """Return the canonical document payload, raising ``KeyError`` if it is absent."""
        document = self.repository.get_document(structure_document_id)
        if document is None:
            raise KeyError(structure_document_id)
        return document.model_dump(mode="json")

    def get(self, structure_document_id: str, *, include: list[str] | set[str] | None = None) -> dict[str, Any]:
        """Return a document bundle, optionally including only the requested child collections."""
        include_set: set[str] | None = None
        if include is not None:
            include_set = {item for item in include if item in _CHILD_FIELDS}
        bundle = self.repository.get_bundle(structure_document_id, include=include_set)
        if bundle is None:
            raise KeyError(structure_document_id)
        return bundle.model_dump(mode="json")

    def list(
        self,
        *,
        profile_id: str | None = None,
        collection_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List structure documents with optional profile/collection/status filters and pagination."""
        documents, total = self.repository.list_documents(
            profile_id=profile_id,
            collection_id=collection_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return {
            "documents": [doc.model_dump(mode="json") for doc in documents],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def delete(self, structure_document_id: str, *, actor: str = "service", roles: set[str] | None = None) -> dict[str, Any]:
        """Delete a structure document and its children, emitting a delete audit event."""
        deleted = self.repository.delete_document(structure_document_id)
        if not deleted:
            raise KeyError(structure_document_id)
        self._audit(actor=actor, roles=roles, action="delete", sdid=structure_document_id)
        return {"structure_document_id": structure_document_id, "deleted": True}

    def list_pages(self, structure_document_id: str) -> dict[str, Any]:
        """Return page records for a document, raising ``KeyError`` if the document is absent."""
        if self.repository.get_document(structure_document_id) is None:
            raise KeyError(structure_document_id)
        pages = self.repository.list_pages(structure_document_id)
        return {
            "structure_document_id": structure_document_id,
            "pages": [page.model_dump(mode="json") for page in pages],
            "count": len(pages),
        }

    def list_sections(self, structure_document_id: str) -> dict[str, Any]:
        """Return section records for a document, raising ``KeyError`` if the document is absent."""
        if self.repository.get_document(structure_document_id) is None:
            raise KeyError(structure_document_id)
        sections = self.repository.list_sections(structure_document_id)
        return {
            "structure_document_id": structure_document_id,
            "sections": [section.model_dump(mode="json") for section in sections],
            "count": len(sections),
        }

    def outline(self, structure_document_id: str) -> dict[str, Any]:
        """Return the section hierarchy as a nested tree (design brief §13 structure_outline_get)."""
        if self.repository.get_document(structure_document_id) is None:
            raise KeyError(structure_document_id)
        sections = self.repository.list_sections(structure_document_id)
        return {
            "structure_document_id": structure_document_id,
            "outline": _build_outline(sections),
        }

    def health(self) -> dict[str, Any]:
        """Return structure-subsystem health including the canonical store probe."""
        probe = self.repository.health()
        return {"component": "structure", "schema_version": SCHEMA_VERSION, **probe}


def _build_outline(sections: list[StructureSection]) -> list[dict[str, Any]]:
    """Assemble a parent/child tree from a flat section list (design brief §6.8 section hierarchy)."""
    nodes: dict[str, dict[str, Any]] = {}
    for section in sections:
        nodes[section.section_id] = {
            "section_id": section.section_id,
            "title": section.title,
            "level": section.level,
            "section_type": str(section.section_type.value if hasattr(section.section_type, "value") else section.section_type),
            "numbering_label": section.numbering_label,
            "children": [],
        }
    roots: list[dict[str, Any]] = []
    for section in sections:
        node = nodes[section.section_id]
        parent_id = section.parent_section_id
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots
