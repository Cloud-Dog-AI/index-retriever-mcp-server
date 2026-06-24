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

"""Corpus management + analysis (design brief §10; §25 #8/#9).

Pattern analysis is deterministic computation over the persisted canonical structure (no live backends),
so it is fully offline-testable. Long-running batch analysis is driven through the existing job queue by
the transport layer; the computation itself lives here in the service layer.
"""

from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import uuid4

from index_tools.structure import ids
from index_tools.structure.corpus_models import (
    CorpusReport,
    PatternType,
    StructureCorpus,
    StructurePattern,
)
from index_tools.structure.corpus_repository import CorpusRepository
from index_tools.structure.distance import structural_distance
from index_tools.structure.repository import StructureRepository


class CorpusService:
    """Corpus CRUD + corpus-level pattern analysis (transport-neutral)."""

    def __init__(
        self,
        *,
        repository: CorpusRepository | None = None,
        structure_repository: StructureRepository | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        """Bind corpus + structure repositories (defaulting to the platform runtime) and audit logger."""
        self.repository = repository or CorpusRepository()
        self.structures = structure_repository or StructureRepository()
        self.audit_logger = audit_logger

    def _audit(self, *, actor: str, roles: set[str] | None, action: str, target_id: str, **details: Any) -> None:
        logger = self.audit_logger
        log = getattr(logger, "log_admin_action", None) if logger is not None else None
        if callable(log):
            log(actor=actor, roles=set(roles or set()), action=action, target_type="structure_corpus", target_id=target_id, target_name=target_id, **details)

    # -- CRUD ------------------------------------------------------------------

    def create(self, data: dict[str, Any] | StructureCorpus, *, actor: str = "service", roles: set[str] | None = None) -> dict[str, Any]:
        """Create (or replace) a corpus from a payload or model."""
        corpus = data if isinstance(data, StructureCorpus) else StructureCorpus.model_validate(data)
        if not corpus.name or not corpus.profile_id:
            raise ValueError("corpus requires name and profile_id")
        if not corpus.corpus_id:
            corpus.corpus_id = f"corp_{uuid4().hex}"
        corpus.document_count = len(corpus.document_ids)
        stored = self.repository.upsert_corpus(corpus)
        self._audit(actor=actor, roles=roles, action="create", target_id=stored.corpus_id, new_value={"name": stored.name, "documents": stored.document_count})
        return stored.model_dump(mode="json")

    def get(self, corpus_id: str) -> dict[str, Any]:
        corpus = self.repository.get_corpus(corpus_id)
        if corpus is None:
            raise KeyError(corpus_id)
        return corpus.model_dump(mode="json")

    def list(self, *, profile_id: str | None = None, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        corpora, total = self.repository.list_corpora(profile_id=profile_id, limit=limit, offset=offset)
        return {"corpora": [c.model_dump(mode="json") for c in corpora], "total": total, "limit": limit, "offset": offset}

    def update(self, corpus_id: str, updates: dict[str, Any], *, actor: str = "service", roles: set[str] | None = None) -> dict[str, Any]:
        corpus = self.repository.get_corpus(corpus_id)
        if corpus is None:
            raise KeyError(corpus_id)
        data = corpus.model_dump()
        for key in ("name", "description", "collection_id", "document_ids", "status", "metadata"):
            if key in updates:
                data[key] = updates[key]
        updated = StructureCorpus.model_validate(data)
        updated.document_count = len(updated.document_ids)
        self.repository.upsert_corpus(updated)
        self._audit(actor=actor, roles=roles, action="update", target_id=corpus_id)
        return updated.model_dump(mode="json")

    def delete(self, corpus_id: str, *, actor: str = "service", roles: set[str] | None = None) -> dict[str, Any]:
        if not self.repository.delete_corpus(corpus_id):
            raise KeyError(corpus_id)
        self._audit(actor=actor, roles=roles, action="delete", target_id=corpus_id)
        return {"corpus_id": corpus_id, "deleted": True}

    # -- analysis (§10.2/§10.3) ------------------------------------------------

    def analyse(self, corpus_id: str, *, actor: str = "service", roles: set[str] | None = None) -> dict[str, Any]:
        """Compute section/style/layout/table patterns across the corpus and persist them."""
        corpus = self.repository.get_corpus(corpus_id)
        if corpus is None:
            raise KeyError(corpus_id)

        section_sequences: Counter[str] = Counter()
        section_type_dist: Counter[str] = Counter()
        style_class_dist: Counter[str] = Counter()
        block_type_dist: Counter[str] = Counter()
        layout_dist: Counter[str] = Counter()
        table_shape_dist: Counter[str] = Counter()
        section_sequence_details: dict[str, list[dict[str, Any]]] = {}
        section_sequence_docs: dict[str, set[str]] = {}
        section_title_variations: dict[str, dict[int, Counter[str]]] = {}
        document_sequences: list[tuple[str, list[str]]] = []
        analysed = 0

        for sdid in corpus.document_ids:
            bundle = self.structures.get_bundle(sdid)
            if bundle is None:
                continue
            analysed += 1
            seq = [str(s.section_type.value if hasattr(s.section_type, "value") else s.section_type) for s in bundle.sections]
            document_sequences.append((sdid, seq))
            if seq:
                signature = "->".join(seq)
                section_sequences[signature] += 1
                section_sequence_docs.setdefault(signature, set()).add(sdid)
                section_sequence_details.setdefault(
                    signature,
                    [
                        {
                            "order": order,
                            "section_type": seq[order],
                            "title": section.title,
                            "normalised_title": section.normalised_title,
                            "level": section.level,
                        }
                        for order, section in enumerate(bundle.sections)
                    ],
                )
                title_variations = section_title_variations.setdefault(signature, {})
                for order, section in enumerate(bundle.sections):
                    title = str(section.title or section.normalised_title or "").strip()
                    if title:
                        title_variations.setdefault(order, Counter())[title] += 1
            for s in seq:
                section_type_dist[s] += 1
            for st in bundle.styles:
                style_class_dist[st.style_class] += 1
            for bl in bundle.blocks:
                block_type_dist[str(bl.block_type.value if hasattr(bl.block_type, "value") else bl.block_type)] += 1
            for pg in bundle.pages:
                layout_dist[f"{pg.width or 0}x{pg.height or 0}:{pg.unit or 'na'}"] += 1
            for tb in bundle.tables:
                table_shape_dist[f"{tb.row_count}r{tb.column_count}c:h{tb.header_rows}"] += 1

        patterns: list[StructurePattern] = []

        def _add(
            ptype: PatternType,
            signature: str,
            support: int,
            detail: dict[str, Any],
            label: str | None = None,
            examples: list[Any] | None = None,
        ) -> None:
            patterns.append(
                StructurePattern(
                    pattern_id=ids._digest("pat", corpus_id, ptype.value, signature),
                    corpus_id=corpus_id,
                    pattern_type=ptype,
                    signature=signature,
                    label=label,
                    support_count=support,
                    document_count=analysed,
                    confidence=round(support / analysed, 4) if analysed else 0.0,
                    examples=list(examples or []),
                    detail=detail,
                )
            )

        for sig, support in section_sequences.most_common():
            variation_counts = {
                str(order): dict(counter.most_common())
                for order, counter in section_title_variations.get(sig, {}).items()
            }
            source_document_ids = sorted(section_sequence_docs.get(sig, set()))
            _add(
                PatternType.section,
                sig,
                support,
                {
                    "sequence": sig.split("->"),
                    "sequence_details": section_sequence_details.get(sig, []),
                    "source_document_ids": source_document_ids,
                    "title_variations": variation_counts,
                },
                label="section-sequence",
                examples=[
                    {"structure_document_id": doc_id}
                    for doc_id in source_document_ids[:5]
                ],
            )
        for cls, support in style_class_dist.most_common():
            _add(PatternType.style, cls, support, {"style_class": cls}, label="style-class")
        for sig, support in layout_dist.most_common():
            _add(PatternType.layout, sig, support, {"page_geometry": sig}, label="page-geometry")
        for sig, support in table_shape_dist.most_common():
            _add(PatternType.table, sig, support, {"table_shape": sig}, label="table-shape")

        dominant = section_sequences.most_common(1)
        # -- structural commonality / variation / pairwise distance (design brief §10.3) --
        commonality_score, variation_score, mean_pairwise_distance, distance_matrix = _score_structure(
            document_sequences=document_sequences,
            dominant_support=dominant[0][1] if dominant else 0,
            document_count=analysed,
            distinct_signatures=len(section_sequences),
        )

        self.repository.replace_patterns(corpus_id, patterns)
        # mark corpus analysed
        corpus.status = "analysed"
        corpus.metadata["last_analysis_pattern_count"] = len(patterns)
        corpus.metadata["commonality_score"] = commonality_score
        corpus.metadata["variation_score"] = variation_score
        corpus.metadata["mean_pairwise_distance"] = mean_pairwise_distance
        self.repository.upsert_corpus(corpus)
        self._audit(actor=actor, roles=roles, action="analyse", target_id=corpus_id, new_value={"patterns": len(patterns), "documents": analysed})

        report = CorpusReport(
            corpus_id=corpus_id,
            document_count=analysed,
            pattern_count=len(patterns),
            section_type_distribution=dict(section_type_dist),
            style_class_distribution=dict(style_class_dist),
            block_type_distribution=dict(block_type_dist),
            dominant_section_sequence=dominant[0][0].split("->") if dominant else [],
            patterns=patterns,
            commonality_score=commonality_score,
            variation_score=variation_score,
            mean_pairwise_distance=mean_pairwise_distance,
            distance_matrix=distance_matrix,
        )
        return report.model_dump(mode="json")

    def patterns_get(self, corpus_id: str, *, pattern_type: str | None = None) -> dict[str, Any]:
        if self.repository.get_corpus(corpus_id) is None:
            raise KeyError(corpus_id)
        patterns = self.repository.list_patterns(corpus_id, pattern_type=pattern_type)
        return {"corpus_id": corpus_id, "patterns": [p.model_dump(mode="json") for p in patterns], "count": len(patterns)}


def _score_structure(
    *,
    document_sequences: list[tuple[str, list[str]]],
    dominant_support: int,
    document_count: int,
    distinct_signatures: int,
) -> tuple[float, float, float, list[dict[str, Any]]]:
    """Compute commonality/variation scores and the pairwise structural-distance matrix (§10.3).

    ``commonality_score`` is the support of the dominant section-sequence over the document
    count; ``variation_score`` is its complement (``1 - commonality``). The distance matrix
    holds the normalised structural distance for every unordered document pair, and
    ``mean_pairwise_distance`` is their mean (``0.0`` when fewer than two documents).
    Returns ``(commonality_score, variation_score, mean_pairwise_distance, distance_matrix)``.
    """
    # req: FR-009
    commonality_score = round(dominant_support / document_count, 6) if document_count else 0.0
    variation_score = round(1.0 - commonality_score, 6)

    distance_matrix: list[dict[str, Any]] = []
    distances: list[float] = []
    for i in range(len(document_sequences)):
        sdid_a, seq_a = document_sequences[i]
        for j in range(i + 1, len(document_sequences)):
            sdid_b, seq_b = document_sequences[j]
            distance = structural_distance(seq_a, seq_b)
            distances.append(distance)
            distance_matrix.append({"a": sdid_a, "b": sdid_b, "distance": distance})

    mean_pairwise_distance = round(sum(distances) / len(distances), 6) if distances else 0.0
    return commonality_score, variation_score, mean_pairwise_distance, distance_matrix
