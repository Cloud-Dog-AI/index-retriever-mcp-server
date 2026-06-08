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

"""Persistence for corpus / pattern / template through cloud_dog_db (design brief §7.1, §10, §11)."""

from __future__ import annotations

from typing import Any

from index_tools.db.corpus_models import StructureCorpusRow, StructurePatternRow, StructureTemplateRow
from index_tools.db.runtime import PlatformDatabaseRuntime, initialise_database
from index_tools.structure.corpus_models import (
    StructureCorpus,
    StructurePattern,
    StructureTemplate,
)


class CorpusRepository:
    """CRUD persistence for corpora, patterns and templates via the cloud_dog_db sync session."""

    def __init__(self, runtime: PlatformDatabaseRuntime | None = None) -> None:
        """Optionally bind a runtime; otherwise the cached platform runtime is used."""
        self._runtime = runtime

    def _sm(self) -> Any:
        return (self._runtime or initialise_database()).session_manager

    # -- corpora ---------------------------------------------------------------

    def upsert_corpus(self, corpus: StructureCorpus) -> StructureCorpus:
        """Create or replace a corpus row by corpus_id."""
        with self._sm().session() as session:
            session.query(StructureCorpusRow).filter(
                StructureCorpusRow.corpus_id == corpus.corpus_id
            ).delete(synchronize_session=False)
            session.add(
                StructureCorpusRow(
                    corpus_id=corpus.corpus_id,
                    profile_id=corpus.profile_id,
                    collection_id=corpus.collection_id,
                    name=corpus.name,
                    status=corpus.status,
                    document_count=corpus.document_count,
                    payload=corpus.model_dump(mode="json"),
                )
            )
        return corpus

    def get_corpus(self, corpus_id: str) -> StructureCorpus | None:
        with self._sm().session() as session:
            row = (
                session.query(StructureCorpusRow)
                .filter(StructureCorpusRow.corpus_id == corpus_id)
                .first()
            )
            return StructureCorpus.model_validate(row.payload) if row is not None else None

    def list_corpora(self, *, profile_id: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[StructureCorpus], int]:
        with self._sm().session() as session:
            query = session.query(StructureCorpusRow)
            if profile_id:
                query = query.filter(StructureCorpusRow.profile_id == profile_id)
            total = query.count()
            rows = query.order_by(StructureCorpusRow.id.desc()).limit(max(1, limit)).offset(max(0, offset)).all()
            return [StructureCorpus.model_validate(r.payload) for r in rows], total

    def delete_corpus(self, corpus_id: str) -> bool:
        with self._sm().session() as session:
            exists = (
                session.query(StructureCorpusRow).filter(StructureCorpusRow.corpus_id == corpus_id).first()
                is not None
            )
            if exists:
                session.query(StructureCorpusRow).filter(
                    StructureCorpusRow.corpus_id == corpus_id
                ).delete(synchronize_session=False)
                session.query(StructurePatternRow).filter(
                    StructurePatternRow.corpus_id == corpus_id
                ).delete(synchronize_session=False)
        return exists

    # -- patterns --------------------------------------------------------------

    def replace_patterns(self, corpus_id: str, patterns: list[StructurePattern]) -> None:
        """Replace all patterns for a corpus."""
        with self._sm().session() as session:
            session.query(StructurePatternRow).filter(
                StructurePatternRow.corpus_id == corpus_id
            ).delete(synchronize_session=False)
            for pattern in patterns:
                session.add(
                    StructurePatternRow(
                        pattern_id=pattern.pattern_id,
                        corpus_id=corpus_id,
                        pattern_type=str(pattern.pattern_type.value if hasattr(pattern.pattern_type, "value") else pattern.pattern_type),
                        signature=pattern.signature[:256],
                        support_count=pattern.support_count,
                        confidence=pattern.confidence,
                        payload=pattern.model_dump(mode="json"),
                    )
                )

    def list_patterns(self, corpus_id: str, *, pattern_type: str | None = None) -> list[StructurePattern]:
        with self._sm().session() as session:
            query = session.query(StructurePatternRow).filter(StructurePatternRow.corpus_id == corpus_id)
            if pattern_type:
                query = query.filter(StructurePatternRow.pattern_type == pattern_type)
            rows = query.order_by(StructurePatternRow.support_count.desc(), StructurePatternRow.id.asc()).all()
            return [StructurePattern.model_validate(r.payload) for r in rows]

    # -- templates -------------------------------------------------------------

    def upsert_template(self, template: StructureTemplate) -> StructureTemplate:
        with self._sm().session() as session:
            session.query(StructureTemplateRow).filter(
                StructureTemplateRow.template_id == template.template_id
            ).delete(synchronize_session=False)
            session.add(
                StructureTemplateRow(
                    template_id=template.template_id,
                    corpus_id=template.corpus_id,
                    profile_id=template.profile_id,
                    name=template.name,
                    confidence=template.confidence,
                    payload=template.model_dump(mode="json"),
                )
            )
        return template

    def get_template(self, template_id: str) -> StructureTemplate | None:
        with self._sm().session() as session:
            row = (
                session.query(StructureTemplateRow)
                .filter(StructureTemplateRow.template_id == template_id)
                .first()
            )
            return StructureTemplate.model_validate(row.payload) if row is not None else None

    def list_templates(self, *, profile_id: str | None = None, corpus_id: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[StructureTemplate], int]:
        with self._sm().session() as session:
            query = session.query(StructureTemplateRow)
            if profile_id:
                query = query.filter(StructureTemplateRow.profile_id == profile_id)
            if corpus_id:
                query = query.filter(StructureTemplateRow.corpus_id == corpus_id)
            total = query.count()
            rows = query.order_by(StructureTemplateRow.id.desc()).limit(max(1, limit)).offset(max(0, offset)).all()
            return [StructureTemplate.model_validate(r.payload) for r in rows], total
