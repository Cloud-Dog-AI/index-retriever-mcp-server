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

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from index_tools.db.models import IndexPlatformDbState
from index_tools.db.runtime import initialise_database, shutdown_database


_BASELINE_REVISION = "20260305_0001"


def _expected_head() -> str:
    """Current Alembic head, derived from the migration scripts (robust to new migrations)."""
    from alembic.script import ScriptDirectory

    from index_tools.db.runtime import _migration_script_location

    return ScriptDirectory(_migration_script_location()).get_current_head()


def _configure_sqlite_env(monkeypatch, db_path: Path) -> None:
    monkeypatch.setenv("CLOUD_DOG_DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG_DB__DATABASE", str(db_path))
    monkeypatch.setenv("CLOUD_DOG__DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG__DB__DATABASE", str(db_path))
    monkeypatch.delenv("CLOUD_DOG__DB__URL", raising=False)
    monkeypatch.delenv("CLOUD_DOG_DB__URL", raising=False)
    monkeypatch.delenv("CLOUD_DOG__INDEX__DB__URL", raising=False)
    monkeypatch.delenv("INDEX_RETRIEVER_DB_URL", raising=False)
    monkeypatch.delenv("CLOUD_DOG_DB__HOST", raising=False)
    monkeypatch.delenv("CLOUD_DOG_DB__PORT", raising=False)
    monkeypatch.delenv("CLOUD_DOG_DB__USERNAME", raising=False)
    monkeypatch.delenv("CLOUD_DOG_DB__PASSWORD", raising=False)
    monkeypatch.delenv("CLOUD_DOG__DB__HOST", raising=False)
    monkeypatch.delenv("CLOUD_DOG__DB__PORT", raising=False)
    monkeypatch.delenv("CLOUD_DOG__DB__USERNAME", raising=False)
    monkeypatch.delenv("CLOUD_DOG__DB__PASSWORD", raising=False)
    monkeypatch.delenv("DB_URL", raising=False)


def test_st_db_01_migration_upgrade_on_fresh_sqlite(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "index-retriever-st-migration.db"
    _configure_sqlite_env(monkeypatch, db_path)

    runtime = initialise_database(force_reinit=True)
    try:
        assert db_path.exists() is True
        with runtime.engine.connect() as conn:
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        # Migrations must upgrade a fresh database to the current head (now includes the
        # W28E-603 structure-foundation migration chained off the baseline).
        assert revision == _expected_head()
    finally:
        shutdown_database()


def test_st_db_02_crud_via_session_manager(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "index-retriever-st-crud.db"
    _configure_sqlite_env(monkeypatch, db_path)

    runtime = initialise_database(force_reinit=True)
    try:
        with runtime.session_manager.session() as session:
            session.add(IndexPlatformDbState(service="index-st", status="ready"))

        with runtime.session_manager.session() as session:
            row = session.query(IndexPlatformDbState).filter_by(service="index-st").one()
            row.status = "verified"

        with runtime.session_manager.session() as session:
            verified = session.query(IndexPlatformDbState).filter_by(service="index-st").one()
            assert verified.status == "verified"
    finally:
        shutdown_database()
