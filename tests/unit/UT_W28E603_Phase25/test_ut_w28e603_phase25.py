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

"""W28E-603 Phases 2-5 unit tests: structure extraction, corpus analysis, template generation/export
(design brief §9/§10/§11; §25 #2/#3/#8/#9/#10). Offline-deterministic via the internal provider + sqlite."""

from __future__ import annotations

from pathlib import Path

import pytest

from index_tools.db.runtime import initialise_database, shutdown_database
from index_tools.structure import StructureService
from index_tools.structure.extract import normalise_text_to_bundle


def _configure_sqlite_env(monkeypatch, db_path: Path) -> None:
    monkeypatch.setenv("CLOUD_DOG_DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG_DB__DATABASE", str(db_path))
    monkeypatch.setenv("CLOUD_DOG__DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG__DB__DATABASE", str(db_path))
    for name in ("CLOUD_DOG__DB__URL", "CLOUD_DOG_DB__URL", "DB_URL", "CLOUD_DOG_DB__HOST"):
        monkeypatch.delenv(name, raising=False)


class _CapturingAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def log_admin_action(self, **kwargs) -> None:
        self.events.append(kwargs)


@pytest.fixture()
def service(monkeypatch, tmp_path: Path):
    _configure_sqlite_env(monkeypatch, tmp_path / "w28e603-p25.db")
    initialise_database(force_reinit=True)
    audit = _CapturingAudit()
    svc = StructureService(audit_logger=audit)
    try:
        yield svc, audit
    finally:
        shutdown_database()


_DOC1 = """# Introduction
Intro paragraph one.

# Scope
Scope text.

| col_a | col_b |
| 1 | 2 |
"""
_DOC2 = """# Introduction
Another intro.

# Scope
More scope.
"""


# -- extraction (no DB) --------------------------------------------------------

def test_normalise_text_blocks_sections_tables() -> None:
    bundle = normalise_text_to_bundle(_DOC1, profile="p", collection="c", source_filename="d1.md")
    assert bundle.document.extractor_provider == "internal"
    assert bundle.document.source_hash
    assert len(bundle.sections) == 2
    assert [s.section_type.value for s in bundle.sections] == ["introduction", "scope"]
    assert len(bundle.tables) == 1 and bundle.tables[0].column_count == 2
    assert any(b.block_type.value == "table" for b in bundle.blocks)
    assert bundle.extractor_runs and bundle.extractor_runs[0].provider == "internal"


def test_extract_text_persists_and_audits(service) -> None:
    svc, audit = service
    out = svc.extract_text(_DOC1, profile="default", collection="docs", source_filename="d1.md", actor="t", roles={"admin"})
    sdid = out["document"]["structure_document_id"]
    got = svc.get(sdid)
    assert len(got["sections"]) == 2 and len(got["blocks"]) >= 3
    assert audit.events[-1]["action"] == "create"


# -- corpus analysis -----------------------------------------------------------

def _two_doc_corpus(svc) -> str:
    id1 = svc.extract_text(_DOC1, profile="default", collection="docs", source_filename="d1.md", actor="t", roles={"admin"})["document"]["structure_document_id"]
    id2 = svc.extract_text(_DOC2, profile="default", collection="docs", source_filename="d2.md", actor="t", roles={"admin"})["document"]["structure_document_id"]
    corp = svc.corpus.create({"name": "specs", "profile_id": "default", "collection_id": "docs", "document_ids": [id1, id2]}, actor="t", roles={"admin"})
    return corp["corpus_id"]


def test_corpus_create_get_list(service) -> None:
    svc, _ = service
    cid = _two_doc_corpus(svc)
    assert svc.corpus.get(cid)["document_count"] == 2
    listing = svc.corpus.list(profile_id="default")
    assert listing["total"] == 1 and listing["corpora"][0]["corpus_id"] == cid


def test_corpus_analyse_produces_patterns(service) -> None:
    svc, _ = service
    cid = _two_doc_corpus(svc)
    report = svc.corpus.analyse(cid, actor="t", roles={"admin"})
    assert report["document_count"] == 2
    assert report["pattern_count"] >= 1
    assert report["dominant_section_sequence"] == ["introduction", "scope"]
    assert report["section_type_distribution"]["introduction"] == 2
    section_patterns = svc.corpus.patterns_get(cid, pattern_type="section")
    assert section_patterns["count"] == 1
    assert section_patterns["patterns"][0]["support_count"] == 2
    assert section_patterns["patterns"][0]["confidence"] == 1.0


def test_corpus_delete_removes_patterns(service) -> None:
    svc, audit = service
    cid = _two_doc_corpus(svc)
    svc.corpus.analyse(cid, actor="t", roles={"admin"})
    assert svc.corpus.delete(cid, actor="t", roles={"admin"})["deleted"] is True
    with pytest.raises(KeyError):
        svc.corpus.get(cid)


def test_corpus_create_requires_name_and_profile(service) -> None:
    svc, _ = service
    with pytest.raises(ValueError):
        svc.corpus.create({"name": "", "profile_id": ""}, actor="t", roles={"admin"})


# -- templates -----------------------------------------------------------------

def test_template_generate_and_export(service) -> None:
    svc, _ = service
    cid = _two_doc_corpus(svc)
    svc.corpus.analyse(cid, actor="t", roles={"admin"})
    tmpl = svc.templates.generate(cid, name="Spec Template", actor="t", roles={"admin"})
    tid = tmpl["template_id"]
    assert len(tmpl["sections"]) == 2
    assert tmpl["sections"][0]["section_type"] == "introduction"
    assert tmpl["confidence"] == 1.0

    fetched = svc.templates.get(tid)
    assert fetched["template_id"] == tid
    listing = svc.templates.list(corpus_id=cid)
    assert listing["total"] == 1

    md = svc.templates.export(tid, format="markdown")
    assert md["format"] == "markdown" and "Section blueprint" in md["content"]
    js = svc.templates.export(tid, format="json")
    assert js["format"] == "json" and '"template_id"' in js["content"]


def test_template_generate_requires_analysis(service) -> None:
    svc, _ = service
    cid = _two_doc_corpus(svc)
    # no analyse() called -> no patterns
    with pytest.raises(ValueError):
        svc.templates.generate(cid, actor="t", roles={"admin"})


def test_template_export_bad_format(service) -> None:
    svc, _ = service
    cid = _two_doc_corpus(svc)
    svc.corpus.analyse(cid, actor="t", roles={"admin"})
    tid = svc.templates.generate(cid, actor="t", roles={"admin"})["template_id"]
    with pytest.raises(ValueError):
        svc.templates.export(tid, format="pdf")
