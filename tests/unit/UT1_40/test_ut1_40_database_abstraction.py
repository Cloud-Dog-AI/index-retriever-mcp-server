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

from index_tools.db.models import IndexPlatformDbState
from index_tools.db.runtime import database_health, initialise_database, shutdown_database
import pytest


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_ut_db_01_engine_factory_creates_sqlite_engine(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "index-retriever-ut.db"
    _configure_sqlite_env(monkeypatch, db_path)

    runtime = initialise_database(force_reinit=True)
    try:
        assert runtime.engine.url.get_backend_name() == "sqlite"
        health = database_health(runtime)
        assert health["ok"] is True
    finally:
        shutdown_database()
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_ut_db_02_session_manager_roundtrip(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "index-retriever-ut-roundtrip.db"
    _configure_sqlite_env(monkeypatch, db_path)

    runtime = initialise_database(force_reinit=True)
    try:
        with runtime.session_manager.session() as session:
            session.add(IndexPlatformDbState(service="index-retriever-mcp-server", status="ready"))

        with runtime.session_manager.session() as session:
            item = (
                session.query(IndexPlatformDbState)
                .filter(IndexPlatformDbState.service == "index-retriever-mcp-server")
                .one()
            )
            assert item.status == "ready"
    finally:
        shutdown_database()
