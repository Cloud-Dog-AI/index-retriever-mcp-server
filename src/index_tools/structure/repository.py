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

"""Persistence repository for canonical document structure (design brief §7.1).

Routes ALL access through ``cloud_dog_db`` — the cached :func:`initialise_database` runtime
and its ``session_manager.session()`` context manager, identical to the existing
``IndexPlatformDbState`` integration. No backend-specific clients are instantiated here
(RULES §1.4 / design brief §7.1). The full canonical object is stored in each row's JSON
``payload`` and reconstructed on read, so the model round-trips exactly (§6.8).
"""

from __future__ import annotations

from typing import Any

from index_tools.db.runtime import PlatformDatabaseRuntime, database_health, initialise_database
from index_tools.db.structure_models import (
    CHILD_ROW_TYPES,
    StructureBlockRow,
    StructureDocumentRow,
    StructureExtractorRunRow,
    StructureFigureRow,
    StructurePageRow,
    StructureRelationRow,
    StructureSectionRow,
    StructureStyleRow,
    StructureTableRow,
)
from index_tools.structure.models import (
    StructureBlock,
    StructureBundle,
    StructureDocument,
    StructureExtractorRun,
    StructureFigure,
    StructurePage,
    StructureRelation,
    StructureSection,
    StructureStyle,
    StructureTable,
)


class StructureRepository:
    """CRUD persistence for structure bundles via the cloud_dog_db sync session."""

    def __init__(self, runtime: PlatformDatabaseRuntime | None = None) -> None:
        """Optionally bind a runtime; otherwise the cached platform runtime is used."""
        self._runtime = runtime

    def _session_manager(self) -> Any:
        runtime = self._runtime or initialise_database()
        return runtime.session_manager

    # -- writes ----------------------------------------------------------------

    def create_bundle(self, bundle: StructureBundle) -> StructureBundle:
        """Persist a bundle, replacing any prior rows for the same document id (idempotent re-extract)."""
        sdid = bundle.document.structure_document_id
        with self._session_manager().session() as session:
            self._delete_rows(session, sdid)
            doc = bundle.document
            session.add(
                StructureDocumentRow(
                    structure_document_id=sdid,
                    profile_id=doc.profile_id,
                    collection_id=doc.collection_id,
                    source_document_id=doc.source_document_id,
                    file_id=doc.file_id,
                    source_hash=doc.source_hash or "",
                    extractor_provider=doc.extractor_provider or "manual",
                    schema_version=doc.schema_version,
                    status=str(doc.status.value if hasattr(doc.status, "value") else doc.status),
                    page_count=doc.page_count,
                    created_by=doc.created_by,
                    payload=doc.model_dump(mode="json"),
                )
            )
            for page in bundle.pages:
                session.add(
                    StructurePageRow(
                        page_id=page.page_id,
                        structure_document_id=sdid,
                        page_number=page.page_number,
                        payload=page.model_dump(mode="json"),
                    )
                )
            for block in bundle.blocks:
                session.add(
                    StructureBlockRow(
                        block_id=block.block_id,
                        structure_document_id=sdid,
                        page_id=block.page_id or None,
                        section_id=block.section_id,
                        block_type=str(block.block_type.value if hasattr(block.block_type, "value") else block.block_type),
                        reading_order_index=block.reading_order_index,
                        payload=block.model_dump(mode="json"),
                    )
                )
            for section in bundle.sections:
                session.add(
                    StructureSectionRow(
                        section_id=section.section_id,
                        structure_document_id=sdid,
                        parent_section_id=section.parent_section_id,
                        level=section.level,
                        section_type=str(section.section_type.value if hasattr(section.section_type, "value") else section.section_type),
                        payload=section.model_dump(mode="json"),
                    )
                )
            for style in bundle.styles:
                session.add(
                    StructureStyleRow(
                        style_id=style.style_id,
                        structure_document_id=sdid,
                        style_class=style.style_class,
                        payload=style.model_dump(mode="json"),
                    )
                )
            for table in bundle.tables:
                session.add(
                    StructureTableRow(
                        table_id=table.table_id,
                        structure_document_id=sdid,
                        page_id=table.page_id,
                        payload=table.model_dump(mode="json"),
                    )
                )
            for figure in bundle.figures:
                session.add(
                    StructureFigureRow(
                        figure_id=figure.figure_id,
                        structure_document_id=sdid,
                        page_id=figure.page_id,
                        payload=figure.model_dump(mode="json"),
                    )
                )
            for relation in bundle.relations:
                session.add(
                    StructureRelationRow(
                        relation_id=relation.relation_id,
                        structure_document_id=sdid,
                        relation_type=relation.relation_type,
                        source_id=relation.source_id,
                        target_id=relation.target_id,
                        payload=relation.model_dump(mode="json"),
                    )
                )
            for run in bundle.extractor_runs:
                session.add(
                    StructureExtractorRunRow(
                        extractor_run_id=run.extractor_run_id,
                        structure_document_id=sdid,
                        provider=run.provider,
                        status=str(run.status.value if hasattr(run.status, "value") else run.status),
                        payload=run.model_dump(mode="json"),
                    )
                )
        return bundle

    def delete_document(self, structure_document_id: str) -> bool:
        """Delete a document and all child rows. Returns True if the document existed."""
        with self._session_manager().session() as session:
            exists = (
                session.query(StructureDocumentRow)
                .filter(StructureDocumentRow.structure_document_id == structure_document_id)
                .first()
                is not None
            )
            if exists:
                self._delete_rows(session, structure_document_id)
        return exists

    @staticmethod
    def _delete_rows(session: Any, structure_document_id: str) -> None:
        session.query(StructureDocumentRow).filter(
            StructureDocumentRow.structure_document_id == structure_document_id
        ).delete(synchronize_session=False)
        for row_type in CHILD_ROW_TYPES.values():
            session.query(row_type).filter(
                row_type.structure_document_id == structure_document_id
            ).delete(synchronize_session=False)

    # -- reads -----------------------------------------------------------------

    def get_document(self, structure_document_id: str) -> StructureDocument | None:
        """Return the canonical document for an id, or ``None`` if it does not exist."""
        with self._session_manager().session() as session:
            row = (
                session.query(StructureDocumentRow)
                .filter(StructureDocumentRow.structure_document_id == structure_document_id)
                .first()
            )
            if row is None:
                return None
            return StructureDocument.model_validate(row.payload)

    def get_bundle(self, structure_document_id: str, *, include: set[str] | None = None) -> StructureBundle | None:
        """Return the document with the requested child collections, or ``None`` if absent."""
        document = self.get_document(structure_document_id)
        if document is None:
            return None
        wanted = include if include is not None else set(CHILD_ROW_TYPES)
        bundle = StructureBundle(document=document)
        if "pages" in wanted:
            bundle.pages = self.list_pages(structure_document_id)
        if "blocks" in wanted:
            bundle.blocks = self._list_children(structure_document_id, StructureBlockRow, StructureBlock)
        if "sections" in wanted:
            bundle.sections = self.list_sections(structure_document_id)
        if "styles" in wanted:
            bundle.styles = self._list_children(structure_document_id, StructureStyleRow, StructureStyle)
        if "tables" in wanted:
            bundle.tables = self._list_children(structure_document_id, StructureTableRow, StructureTable)
        if "figures" in wanted:
            bundle.figures = self._list_children(structure_document_id, StructureFigureRow, StructureFigure)
        if "relations" in wanted:
            bundle.relations = self._list_children(structure_document_id, StructureRelationRow, StructureRelation)
        if "extractor_runs" in wanted:
            bundle.extractor_runs = self._list_children(
                structure_document_id, StructureExtractorRunRow, StructureExtractorRun
            )
        return bundle

    def list_documents(
        self,
        *,
        profile_id: str | None = None,
        collection_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[StructureDocument], int]:
        """Return a page of documents matching the filters together with the total count."""
        with self._session_manager().session() as session:
            query = session.query(StructureDocumentRow)
            if profile_id:
                query = query.filter(StructureDocumentRow.profile_id == profile_id)
            if collection_id:
                query = query.filter(StructureDocumentRow.collection_id == collection_id)
            if status:
                query = query.filter(StructureDocumentRow.status == status)
            total = query.count()
            rows = (
                query.order_by(StructureDocumentRow.id.desc())
                .limit(max(1, limit))
                .offset(max(0, offset))
                .all()
            )
            documents = [StructureDocument.model_validate(row.payload) for row in rows]
        return documents, total

    def list_pages(self, structure_document_id: str) -> list[StructurePage]:
        """Return page records for a document ordered by page number."""
        with self._session_manager().session() as session:
            rows = (
                session.query(StructurePageRow)
                .filter(StructurePageRow.structure_document_id == structure_document_id)
                .order_by(StructurePageRow.page_number.asc())
                .all()
            )
            return [StructurePage.model_validate(row.payload) for row in rows]

    def list_sections(self, structure_document_id: str) -> list[StructureSection]:
        """Return section records for a document ordered by level then insertion order."""
        with self._session_manager().session() as session:
            rows = (
                session.query(StructureSectionRow)
                .filter(StructureSectionRow.structure_document_id == structure_document_id)
                .order_by(StructureSectionRow.level.asc(), StructureSectionRow.id.asc())
                .all()
            )
            return [StructureSection.model_validate(row.payload) for row in rows]

    def _list_children(self, structure_document_id: str, row_type: Any, model_type: Any) -> list[Any]:
        with self._session_manager().session() as session:
            rows = (
                session.query(row_type)
                .filter(row_type.structure_document_id == structure_document_id)
                .order_by(row_type.id.asc())
                .all()
            )
            return [model_type.model_validate(row.payload) for row in rows]

    def health(self) -> dict[str, Any]:
        """Structure-store health via the platform db probe (design brief §13 structure_health)."""
        return database_health(self._runtime)
