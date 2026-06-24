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

"""W28E-1805B unit tests: internal-path output enrichment (language hints, quality score,
token counts), structural-distance scoring, and generated-template replication match
(design brief §9.1/§10.3/§11; §25 #2/#3/#10). Offline-deterministic via the internal provider."""

from __future__ import annotations

from pathlib import Path

import pytest

from index_tools.db.runtime import initialise_database, shutdown_database
from index_tools.structure import StructureService
from index_tools.structure.distance import structural_distance
from index_tools.structure.extract import normalise_text_to_bundle
from index_tools.structure.language import detect_scripts


def _configure_sqlite_env(monkeypatch, db_path: Path) -> None:
    monkeypatch.setenv("CLOUD_DOG_DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG_DB__DATABASE", str(db_path))
    monkeypatch.setenv("CLOUD_DOG__DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG__DB__DATABASE", str(db_path))
    for name in (
        "CLOUD_DOG__DB__URL",
        "CLOUD_DOG_DB__URL",
        "CLOUD_DOG__INDEX__DB__URL",
        "INDEX_RETRIEVER_DB_URL",
        "DB_URL",
        "CLOUD_DOG_DB__HOST",
    ):
        monkeypatch.delenv(name, raising=False)


class _CapturingAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def log_admin_action(self, **kwargs) -> None:
        self.events.append(kwargs)


@pytest.fixture()
def service(monkeypatch, tmp_path: Path):
    _configure_sqlite_env(monkeypatch, tmp_path / "w28e1805b.db")
    initialise_database(force_reinit=True)
    audit = _CapturingAudit()
    svc = StructureService(audit_logger=audit)
    try:
        yield svc, audit
    finally:
        shutdown_database()


_DOC_EN = """# Introduction
This is a well formed English introduction paragraph.

# Scope
The scope section describes the boundaries of the analysis here.
"""
_DOC_FR = """# Introduction
Ceci est une introduction en français avec des accents été.

# Scope
La portée décrit les limites de cette analyse pour le projet.
"""
_DOC_RU = "# Введение\nЭто документ написанный на русском языке для проверки.\n"
_DOC_ZH = "# 介绍\n这是一个用于测试的中文文档段落内容示例。\n"
_DOC_AR = "# مقدمة\nهذا مستند مكتوب باللغة العربية لاختبار الكشف عن اللغة.\n"
_DOC_HI = "# परिचय\nयह दस्तावेज़ हिंदी भाषा में लिखा गया परीक्षण के लिए है।\n"
_DOC_MALFORMED = """####### Too Deep Heading
Body text under an over-deep heading line.

#NoSpaceHeading
More body text.
"""


# -- GAP 1a: language detection ------------------------------------------------
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")
def test_detect_scripts_per_language() -> None:
    assert detect_scripts("Hello world this is plain english text") == ["en"]
    assert detect_scripts("Привет мир это русский текст") == ["ru"]
    assert detect_scripts("هذا نص عربي") == ["ar"]
    assert detect_scripts("这是中文文本") == ["zh"]
    assert detect_scripts("यह हिंदी पाठ है") == ["hi"]
    assert detect_scripts("Ceci est écrit en français avec été") == ["fr"]
    assert detect_scripts("") == ["und"]
    assert detect_scripts("12345 !!! ???") == ["und"]


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")
def test_internal_extract_populates_language_hints() -> None:
    bundle_en = normalise_text_to_bundle(_DOC_EN, profile="p", collection="c")
    assert bundle_en.document.language_hints == ["en"]
    bundle_ru = normalise_text_to_bundle(_DOC_RU, profile="p", collection="c")
    assert bundle_ru.document.language_hints == ["ru"]
    bundle_zh = normalise_text_to_bundle(_DOC_ZH, profile="p", collection="c")
    assert bundle_zh.document.language_hints == ["zh"]
    bundle_ar = normalise_text_to_bundle(_DOC_AR, profile="p", collection="c")
    assert bundle_ar.document.language_hints == ["ar"]
    bundle_hi = normalise_text_to_bundle(_DOC_HI, profile="p", collection="c")
    assert bundle_hi.document.language_hints == ["hi"]
    bundle_fr = normalise_text_to_bundle(_DOC_FR, profile="p", collection="c")
    assert bundle_fr.document.language_hints == ["fr"]


# -- GAP 1b: quality score -----------------------------------------------------
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")
@pytest.mark.req("FR-014")
def test_internal_extract_quality_score_and_detail() -> None:
    bundle = normalise_text_to_bundle(_DOC_EN, profile="p", collection="c")
    doc = bundle.document
    assert doc.quality_score is not None
    assert 0.0 <= doc.quality_score <= 1.0
    quality = doc.metadata["quality"]
    assert quality["section_completeness"] == 1.0  # both sections titled
    assert quality["heading_consistency"] == 1.0  # h1 -> h1, no skipped level
    assert quality["block_coverage"] == 1.0
    assert quality["malformed_flags"] == []
    # well-formed doc with all signals at 1.0 and no penalty
    assert doc.quality_score == 1.0


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")
@pytest.mark.req("FR-014")
def test_internal_extract_flags_malformed_input() -> None:
    bundle = normalise_text_to_bundle(_DOC_MALFORMED, profile="p", collection="c")
    doc = bundle.document
    flags = doc.metadata["quality"]["malformed_flags"]
    assert "overdeep_heading" in flags
    assert "heading_without_space" in flags
    assert doc.metadata["quality_flags"] == sorted(flags)
    # malformed input carries a penalty -> strictly below the clean-doc score
    assert doc.quality_score < 1.0


# -- GAP 1c: token counts ------------------------------------------------------
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-014")
def test_internal_extract_token_counts() -> None:
    bundle = normalise_text_to_bundle(_DOC_EN, profile="p", collection="c")
    for block in bundle.blocks:
        assert "token_count" in block.metadata
        assert block.metadata["token_count"] == len(block.text.split())
    document_total = bundle.document.metadata["token_count"]
    assert document_total == sum(b.metadata["token_count"] for b in bundle.blocks)
    assert document_total > 0


# -- GAP 2: structural distance + commonality/variation ------------------------
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")
def test_structural_distance_formula() -> None:
    assert structural_distance([], []) == 0.0
    assert structural_distance(["a", "b"], ["a", "b"]) == 0.0
    assert structural_distance(["a", "b"], ["c", "d"]) == 1.0
    # one of two positions differs -> 1/2
    assert structural_distance(["a", "b"], ["a", "c"]) == 0.5
    # one insertion against an empty sequence -> max distance
    assert structural_distance(["a"], []) == 1.0
    # length-normalised: 1 edit over the longer (len 3) sequence
    assert structural_distance(["a", "b", "c"], ["a", "b"]) == round(1 / 3, 6)


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")
def test_corpus_analyse_commonality_variation_distance(service) -> None:
    svc, _ = service
    same1 = svc.extract_text(_DOC_EN, profile="default", collection="docs", source_filename="s1.md", actor="t", roles={"admin"})["document"]["structure_document_id"]
    same2 = svc.extract_text("# Introduction\nIntro two.\n\n# Scope\nScope two.\n", profile="default", collection="docs", source_filename="s2.md", actor="t", roles={"admin"})["document"]["structure_document_id"]
    # a third doc with a different structure (single unknown section)
    other = svc.extract_text("# Situation\nDifferent shape.\n", profile="default", collection="docs", source_filename="s3.md", actor="t", roles={"admin"})["document"]["structure_document_id"]
    cid = svc.corpus.create(
        {"name": "mixed", "profile_id": "default", "collection_id": "docs", "document_ids": [same1, same2, other]},
        actor="t", roles={"admin"},
    )["corpus_id"]
    report = svc.corpus.analyse(cid, actor="t", roles={"admin"})

    # dominant sequence (introduction->scope) is supported by 2 of 3 documents
    assert report["commonality_score"] == round(2 / 3, 6)
    assert report["variation_score"] == round(1 - 2 / 3, 6)
    # 3 documents -> 3 unordered pairs in the matrix
    assert len(report["distance_matrix"]) == 3
    for entry in report["distance_matrix"]:
        assert set(entry) == {"a", "b", "distance"}
        assert 0.0 <= entry["distance"] <= 1.0
    assert 0.0 <= report["mean_pairwise_distance"] <= 1.0
    # the two identical-structure docs have distance 0
    pair_same = next(e for e in report["distance_matrix"] if {e["a"], e["b"]} == {same1, same2})
    assert pair_same["distance"] == 0.0

    # persisted on corpus metadata
    corpus = svc.corpus.get(cid)
    assert corpus["metadata"]["commonality_score"] == round(2 / 3, 6)
    assert corpus["metadata"]["variation_score"] == round(1 - 2 / 3, 6)


# -- GAP 3: template replication match -----------------------------------------
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-014")
def test_template_match_scores_replication(service) -> None:
    svc, _ = service
    id1 = svc.extract_text(_DOC_EN, profile="default", collection="docs", source_filename="m1.md", actor="t", roles={"admin"})["document"]["structure_document_id"]
    id2 = svc.extract_text("# Introduction\nIntro two.\n\n# Scope\nScope two.\n", profile="default", collection="docs", source_filename="m2.md", actor="t", roles={"admin"})["document"]["structure_document_id"]
    cid = svc.corpus.create(
        {"name": "match corpus", "profile_id": "default", "collection_id": "docs", "document_ids": [id1, id2]},
        actor="t", roles={"admin"},
    )["corpus_id"]
    svc.corpus.analyse(cid, actor="t", roles={"admin"})
    tid = svc.templates.generate(cid, name="Match Template", actor="t", roles={"admin"})["template_id"]

    # a document matching the template structure exactly -> perfect score
    perfect = svc.templates.match(tid, id1)
    assert perfect["match_score"] == 1.0
    assert [m["section_type"] for m in perfect["matched"]] == ["introduction", "scope"]
    assert perfect["missing"] == []
    assert perfect["extra"] == []

    # a structurally different document -> lower score, with missing/extra reported
    partial_id = svc.extract_text("# Introduction\nIntro only.\n", profile="default", collection="docs", source_filename="m3.md", actor="t", roles={"admin"})["document"]["structure_document_id"]
    partial = svc.templates.match(tid, partial_id)
    assert 0.0 <= partial["match_score"] < 1.0
    assert any(s["section_type"] == "scope" for s in partial["missing"])


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-014")
def test_template_match_missing_template_or_document_raises(service) -> None:
    svc, _ = service
    id1 = svc.extract_text(_DOC_EN, profile="default", collection="docs", source_filename="x1.md", actor="t", roles={"admin"})["document"]["structure_document_id"]
    cid = svc.corpus.create(
        {"name": "raise corpus", "profile_id": "default", "collection_id": "docs", "document_ids": [id1]},
        actor="t", roles={"admin"},
    )["corpus_id"]
    svc.corpus.analyse(cid, actor="t", roles={"admin"})
    tid = svc.templates.generate(cid, actor="t", roles={"admin"})["template_id"]
    with pytest.raises(KeyError):
        svc.templates.match("tmpl_missing", id1)
    with pytest.raises(KeyError):
        svc.templates.match(tid, "sd_missing")
