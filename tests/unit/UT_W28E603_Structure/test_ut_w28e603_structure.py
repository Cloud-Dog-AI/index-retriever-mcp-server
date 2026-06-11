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

"""W28E-603 Phase 1 unit tests: canonical structure model, deterministic IDs, and
cloud_dog_db-routed persistence/service round-trips (design brief §6, §8.2, §24 Phase 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from index_tools.db.runtime import initialise_database, shutdown_database
from index_tools.structure import (
    SCHEMA_VERSION,
    StructureBlock,
    StructureBundle,
    StructureDocument,
    StructurePage,
    StructureSection,
    StructureService,
    ids,
)


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
        "CLOUD_DOG_DB__HOST",
        "CLOUD_DOG_DB__PORT",
        "CLOUD_DOG_DB__USERNAME",
        "CLOUD_DOG_DB__PASSWORD",
        "CLOUD_DOG__DB__HOST",
        "CLOUD_DOG__DB__PORT",
        "CLOUD_DOG__DB__USERNAME",
        "CLOUD_DOG__DB__PASSWORD",
        "DB_URL",
    ):
        monkeypatch.delenv(name, raising=False)


class _CapturingAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def log_admin_action(self, **kwargs) -> None:
        self.events.append(kwargs)


@pytest.fixture()
def structure_service(monkeypatch, tmp_path: Path):
    _configure_sqlite_env(monkeypatch, tmp_path / "w28e603-ut.db")
    initialise_database(force_reinit=True)
    audit = _CapturingAudit()
    service = StructureService(audit_logger=audit)
    try:
        yield service, audit
    finally:
        shutdown_database()


def _sample_bundle() -> StructureBundle:
    return StructureBundle(
        document=StructureDocument(
            profile_id="default",
            collection_id="docs",
            source_hash="hash-w28e603",
            source_filename="report.pdf",
            extractor_provider="manual",
        ),
        pages=[StructurePage(page_number=1, width=612, height=792), StructurePage(page_number=2)],
        sections=[
            StructureSection(section_id="sec-root", title="Introduction", level=0, numbering_label="1", start_page=1),
            StructureSection(
                section_id="sec-child", title="Scope", level=1, numbering_label="1.1",
                start_page=1, parent_section_id="sec-root",
            ),
        ],
        blocks=[StructureBlock(text="Hello", reading_order_index=0, block_type="paragraph")],
    )


# -- model / id tests (no DB) --------------------------------------------------

def test_schema_version_constant() -> None:
    assert SCHEMA_VERSION == "1.0"
    assert StructureDocument(profile_id="p", collection_id="c").schema_version == "1.0"


def test_deterministic_document_id_is_stable_and_distinct() -> None:
    first = ids.structure_document_id(
        profile_id="p", collection_id="c", source_hash="h", parser_family="manual", schema_version="1.0"
    )
    second = ids.structure_document_id(
        profile_id="p", collection_id="c", source_hash="h", parser_family="manual", schema_version="1.0"
    )
    other = ids.structure_document_id(
        profile_id="p", collection_id="c", source_hash="DIFFERENT", parser_family="manual", schema_version="1.0"
    )
    assert first == second
    assert first != other
    assert first.startswith("sd_")


def test_deterministic_page_and_block_ids() -> None:
    sdid = "sd_x"
    assert ids.page_id(sdid, 1) == ids.page_id(sdid, 1)
    assert ids.page_id(sdid, 1) != ids.page_id(sdid, 2)
    block = ids.block_id(page_id="pg_1", reading_order_index=0, bbox=[0, 0, 1, 1], text="hi", block_type="paragraph")
    assert block.startswith("bk_")


# -- persistence / service round-trips (sqlite via cloud_dog_db) ---------------

def test_create_assigns_ids_and_persists(structure_service) -> None:
    service, audit = structure_service
    created = service.create(_sample_bundle(), actor="tester", roles={"admin"})
    sdid = created["document"]["structure_document_id"]
    # deterministic doc id derived from source_hash
    assert sdid == ids.structure_document_id(
        profile_id="default", collection_id="docs", source_hash="hash-w28e603",
        parser_family="manual", schema_version="1.0",
    )
    assert created["document"]["page_count"] == 2
    assert all(page["structure_document_id"] == sdid for page in created["pages"])
    assert all(page["page_id"] for page in created["pages"])
    # create is audited (acceptance §25.14)
    assert audit.events and audit.events[-1]["action"] == "create"
    assert audit.events[-1]["target_type"] == "structure_document"


def test_get_list_and_include_filtering(structure_service) -> None:
    service, _ = structure_service
    created = service.create(_sample_bundle(), actor="tester", roles={"admin"})
    sdid = created["document"]["structure_document_id"]

    full = service.get(sdid)
    assert len(full["pages"]) == 2 and len(full["sections"]) == 2 and len(full["blocks"]) == 1

    pages_only = service.get(sdid, include=["pages"])
    assert pages_only["pages"] and not pages_only["blocks"] and not pages_only["sections"]

    listing = service.list(profile_id="default")
    assert listing["total"] == 1
    assert listing["documents"][0]["structure_document_id"] == sdid


def test_outline_builds_section_tree(structure_service) -> None:
    service, _ = structure_service
    created = service.create(_sample_bundle(), actor="tester", roles={"admin"})
    outline = service.outline(created["document"]["structure_document_id"])
    roots = outline["outline"]
    assert len(roots) == 1
    assert roots[0]["title"] == "Introduction"
    assert len(roots[0]["children"]) == 1
    assert roots[0]["children"][0]["title"] == "Scope"


def test_pages_and_sections_listing(structure_service) -> None:
    service, _ = structure_service
    sdid = service.create(_sample_bundle(), actor="tester", roles={"admin"})["document"]["structure_document_id"]
    pages = service.list_pages(sdid)
    assert pages["count"] == 2 and pages["pages"][0]["page_number"] == 1
    sections = service.list_sections(sdid)
    assert sections["count"] == 2


def test_idempotent_recreate_keeps_single_document(structure_service) -> None:
    service, _ = structure_service
    first = service.create(_sample_bundle(), actor="tester", roles={"admin"})
    second = service.create(_sample_bundle(), actor="tester", roles={"admin"})
    assert first["document"]["structure_document_id"] == second["document"]["structure_document_id"]
    assert service.list(profile_id="default")["total"] == 1


def test_delete_removes_document_and_children(structure_service) -> None:
    service, audit = structure_service
    sdid = service.create(_sample_bundle(), actor="tester", roles={"admin"})["document"]["structure_document_id"]
    result = service.delete(sdid, actor="tester", roles={"admin"})
    assert result["deleted"] is True
    assert service.list(profile_id="default")["total"] == 0
    assert audit.events[-1]["action"] == "delete"
    with pytest.raises(KeyError):
        service.get(sdid)


def test_missing_document_raises_key_error(structure_service) -> None:
    service, _ = structure_service
    with pytest.raises(KeyError):
        service.get("sd_does_not_exist")
    with pytest.raises(KeyError):
        service.delete("sd_does_not_exist")


def test_create_requires_profile_and_collection(structure_service) -> None:
    service, _ = structure_service
    bad = StructureBundle(document=StructureDocument(profile_id="", collection_id=""))
    with pytest.raises(ValueError):
        service.create(bad, actor="tester", roles={"admin"})


def test_health_reports_structure_component(structure_service) -> None:
    service, _ = structure_service
    health = service.health()
    assert health["component"] == "structure"
    assert health["schema_version"] == "1.0"
    assert health["ok"] is True
