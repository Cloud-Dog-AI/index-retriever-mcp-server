from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from index_tools.db.models import IndexPlatformDbState
from index_tools.db.runtime import initialise_database, shutdown_database


_BASELINE_REVISION = "20260305_0001"


def _configure_sqlite_env(monkeypatch, db_path: Path) -> None:
    monkeypatch.setenv("CLOUD_DOG__DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG__DB__DATABASE", str(db_path))
    monkeypatch.delenv("CLOUD_DOG__DB__URL", raising=False)
    monkeypatch.delenv("CLOUD_DOG_DB__URL", raising=False)
    monkeypatch.delenv("DB_URL", raising=False)


def test_st_db_01_migration_upgrade_on_fresh_sqlite(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "index-retriever-st-migration.db"
    _configure_sqlite_env(monkeypatch, db_path)

    runtime = initialise_database(force_reinit=True)
    try:
        assert db_path.exists() is True
        with runtime.engine.connect() as conn:
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision == _BASELINE_REVISION
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
