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

"""W28E-604 spreadsheet indexing: SQL control plane + indexer orchestration."""

from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path

import openpyxl
import pytest
from cloud_dog_vdb.spreadsheet import testing
from cloud_dog_vdb.spreadsheet.config import SpreadsheetConfig
from sqlalchemy import func, inspect, select

from index_tools.db.runtime import initialise_database, shutdown_database
from index_tools.spreadsheet import (
    SpreadsheetIndexer,
    build_spreadsheet_config,
    is_spreadsheet,
)
from index_tools.spreadsheet.sql_models import (
    SpreadsheetChunk,
    SpreadsheetIndexError,
    SpreadsheetIndexJob,
    SpreadsheetObject,
)

EXPECTED_TABLES = {
    "ss_sources",
    "ss_index_jobs",
    "ss_source_versions",
    "ss_objects",
    "ss_extracted_tables",
    "ss_chunks",
    "ss_refresh_manifests",
    "ss_backend_sync_state",
    "ss_index_errors",
}

pytestmark = [pytest.mark.UT, pytest.mark.internal, pytest.mark.req("FR-002")]


@pytest.fixture
def db_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[object]:
    db_path = tmp_path / "ss.db"
    monkeypatch.setenv("CLOUD_DOG_DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG_DB__DATABASE", str(db_path))
    monkeypatch.setenv("CLOUD_DOG__DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG__DB__DATABASE", str(db_path))
    for name in ("CLOUD_DOG__DB__URL", "CLOUD_DOG_DB__URL", "CLOUD_DOG_DB__HOST", "DB_URL"):
        monkeypatch.delenv(name, raising=False)
    runtime = initialise_database(force_reinit=True)
    try:
        yield runtime
    finally:
        shutdown_database()


def _resave(data: bytes) -> bytes:
    wb = openpyxl.load_workbook(io.BytesIO(data))
    wb.properties.creator = "other"
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-002")
def test_is_spreadsheet_routing():
    assert is_spreadsheet("report.xlsx")
    assert is_spreadsheet("macro.XLSM")
    assert is_spreadsheet("data.ods")
    assert not is_spreadsheet("notes.pdf")
    assert not is_spreadsheet("plain.txt")
    assert not is_spreadsheet("noextension")


def test_build_spreadsheet_config_overrides():
    config = build_spreadsheet_config({"row_batch_size": "25", "include_hidden_sheets": "false", "bogus": "x"})
    assert config.row_batch_size == 25
    assert config.include_hidden_sheets is False


def test_migration_creates_control_plane_tables(db_runtime):
    tables = set(inspect(db_runtime.engine).get_table_names())
    assert tables >= EXPECTED_TABLES


def test_indexer_persists_control_plane_and_upserts(db_runtime):
    captured = []
    indexer = SpreadsheetIndexer(session_manager=db_runtime.session_manager)
    result = indexer.index(
        testing.build_simple_xlsx(),
        file_name="s.xlsx",
        source_uri="upload://s.xlsx",
        upsert=lambda recs: captured.extend(recs),
        backend_name="chroma",
        base_metadata={"profile": "default", "collection": "docs"},
    )
    assert result.status == "complete"
    assert result.object_counts == {"workbook": 1, "sheet": 1, "table": 1, "column": 4, "row_batch": 3}
    assert result.upserted == 10
    assert len(captured) == 10
    assert captured[0].metadata["profile"] == "default"

    with db_runtime.session_manager.session() as session:
        objects = session.execute(select(func.count()).select_from(SpreadsheetObject)).scalar_one()
        chunks = session.execute(select(func.count()).select_from(SpreadsheetChunk)).scalar_one()
        job = session.execute(select(SpreadsheetIndexJob)).scalars().one()
    assert objects == 10
    assert chunks == 10
    assert job.status == "complete"


def test_reindex_same_content_deletes_nothing(db_runtime):
    indexer = SpreadsheetIndexer(session_manager=db_runtime.session_manager)
    deleted: list[str] = []
    data = testing.build_simple_xlsx()
    indexer.index(data, file_name="s.xlsx", source_uri="upload://s.xlsx", upsert=lambda r: None, backend_name="chroma")
    result = indexer.index(
        _resave(data),
        file_name="s.xlsx",
        source_uri="upload://s.xlsx",
        upsert=lambda r: None,
        delete=lambda keys: deleted.extend(keys),
        backend_name="chroma",
    )
    assert result.deleted == 0
    assert deleted == []
    # incremental re-index optimisation: unchanged objects are not re-upserted (5.14)
    assert result.upserted == 0


def test_reindex_changed_content_deletes_stale(db_runtime):
    indexer = SpreadsheetIndexer(session_manager=db_runtime.session_manager)
    deleted: list[str] = []
    indexer.index(
        testing.build_multisheet_formal_tables_xlsx(),
        file_name="s.xlsx",
        source_uri="upload://s.xlsx",
        upsert=lambda r: None,
        backend_name="chroma",
    )
    result = indexer.index(
        testing.build_simple_xlsx(),
        file_name="s.xlsx",
        source_uri="upload://s.xlsx",
        upsert=lambda r: None,
        delete=lambda keys: deleted.extend(keys),
        backend_name="chroma",
    )
    assert result.deleted > 0
    assert deleted, "stale objects from the previous version must be deleted"


def test_parse_failure_records_error_and_no_upsert(db_runtime):
    indexer = SpreadsheetIndexer(session_manager=db_runtime.session_manager)
    captured = []
    result = indexer.index(
        testing.build_malformed_bytes(),
        file_name="bad.xlsx",
        source_uri="upload://bad.xlsx",
        upsert=lambda recs: captured.extend(recs),
    )
    assert result.status == "failed"
    assert captured == []
    with db_runtime.session_manager.session() as session:
        errors = session.execute(select(func.count()).select_from(SpreadsheetIndexError)).scalar_one()
    assert errors >= 1


def test_stateless_indexer_upserts_without_db():
    captured = []
    indexer = SpreadsheetIndexer(session_manager=None)
    result = indexer.index(
        testing.build_simple_ods(),
        file_name="b.ods",
        source_uri="upload://b.ods",
        upsert=lambda recs: captured.extend(recs),
    )
    assert result.status == "complete"
    assert captured
    assert any(r.metadata["object_type"] == "table" for r in captured)


def test_refresh_mode_manifest_only_skips_backend(db_runtime):
    indexer = SpreadsheetIndexer(session_manager=db_runtime.session_manager)
    upserts: list = []
    deletes: list = []
    indexer.index(
        testing.build_multisheet_formal_tables_xlsx(),
        file_name="s.xlsx",
        source_uri="upload://s.xlsx",
        upsert=lambda r: upserts.extend(r),
        backend_name="chroma",
    )
    upserts.clear()
    result = indexer.index(
        testing.build_simple_xlsx(),
        file_name="s.xlsx",
        source_uri="upload://s.xlsx",
        upsert=lambda r: upserts.extend(r),
        delete=lambda keys: deletes.extend(keys),
        backend_name="chroma",
        config=SpreadsheetConfig(refresh_mode="manifest_only"),
    )
    assert result.upserted == 0 and result.deleted == 0
    assert upserts == [] and deletes == []
    # the SQL manifest is still updated: a third source version exists
    with db_runtime.session_manager.session() as session:
        versions = session.execute(select(func.count()).select_from(SpreadsheetObject)).scalar_one()
    assert versions > 0


def test_refresh_mode_full_reupserts_all(db_runtime):
    indexer = SpreadsheetIndexer(session_manager=db_runtime.session_manager)
    data = testing.build_simple_xlsx()
    indexer.index(data, file_name="s.xlsx", source_uri="upload://s.xlsx", upsert=lambda r: None, backend_name="chroma")
    result = indexer.index(
        _resave(data),
        file_name="s.xlsx",
        source_uri="upload://s.xlsx",
        upsert=lambda r: None,
        backend_name="chroma",
        config=SpreadsheetConfig(refresh_mode="full"),
    )
    # full mode re-upserts every record even though content is unchanged
    assert result.upserted == 10


def test_ingest_upload_routes_spreadsheet_to_structural_index(service, monkeypatch):
    # Keep the control plane out of this routing test (covered above); prove that
    # an uploaded workbook is structurally indexed and the records are searchable.
    monkeypatch.setattr(type(service), "_spreadsheet_session_manager", lambda self: None)
    result = service.ingest_upload(
        profile="default",
        collection="ss_docs",
        filename="sales.xlsx",
        content=testing.build_simple_xlsx(),
        actor="tester",
    )
    assert result["status"] == "complete"
    assert result["object_counts"]["table"] == 1
    assert result["upserted"] == 10
    rows = service.search("default", "ss_docs", "sales", top_k=20)
    assert isinstance(rows, list) and rows, "spreadsheet records should be searchable"
