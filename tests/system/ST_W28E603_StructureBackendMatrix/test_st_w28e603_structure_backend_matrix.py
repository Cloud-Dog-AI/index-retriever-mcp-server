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

"""W28E-603 Phase 1 backend-matrix smoke (design brief §24 Phase 1, §7.1).

Runs the canonical structure create/get/list/delete round-trip through cloud_dog_db across
the SQL dialects the existing matrix supports. ``sqlite`` always runs (the guaranteed local
smoke). ``postgresql``/``mysql`` legs run ONLY against an explicitly provided disposable test
DB URL — they SKIP with an explicit reason otherwise (mirrors the VDB-matrix skip pattern in
``tests/w23a_helpers.py``; never targets shared/live backends — RULES/AGENT-LESSONS ST-tier
local-only rule). No silent caps: each skipped leg is reported.
"""

from __future__ import annotations

import os

import pytest

from index_tools.db.runtime import initialise_database, shutdown_database
from index_tools.structure import StructureBundle, StructureDocument, StructurePage, StructureSection, StructureService

# Opt-in disposable test-DB URLs for the non-default legs (point at a throwaway database).
_MATRIX_URL_ENV = {
    "postgresql": "W28E603_MATRIX_POSTGRESQL_URL",
    "mysql": "W28E603_MATRIX_MYSQL_URL",
}

_DIALECTS = ["sqlite", "postgresql", "mysql"]


_DB_ENV_KEYS = (
    "CLOUD_DOG_DB__URL", "CLOUD_DOG_DB__DIALECT", "CLOUD_DOG_DB__HOST", "CLOUD_DOG_DB__PORT",
    "CLOUD_DOG_DB__USERNAME", "CLOUD_DOG_DB__PASSWORD", "CLOUD_DOG_DB__DATABASE",
)


def _configure(monkeypatch, dialect: str, tmp_path) -> str | None:
    """Configure cloud_dog_db env for the dialect. Returns a skip reason, or None to run.

    The postgresql/mysql legs run against a real backend when one is provided, in order:
    (1) an explicit opt-in ``W28E603_MATRIX_{POSTGRESQL,MYSQL}_URL``, or (2) a harness env
    file (e.g. ``--env tests/env-DB-postgresql``) that already configures that dialect (its
    Vault refs resolved to concrete host/credentials). Otherwise the leg SKIPs with a reason.
    """
    # Snapshot any harness-provided DB settings BEFORE clearing them.
    snapshot = {key: os.environ.get(key, "") for key in _DB_ENV_KEYS}
    for name in (*_DB_ENV_KEYS, "CLOUD_DOG__DB__URL", "DB_URL", "CLOUD_DOG__DB__DIALECT", "CLOUD_DOG__DB__DATABASE"):
        monkeypatch.delenv(name, raising=False)

    if dialect == "sqlite":
        monkeypatch.setenv("CLOUD_DOG_DB__DIALECT", "sqlite")
        monkeypatch.setenv("CLOUD_DOG_DB__DATABASE", str(tmp_path / "w28e603-matrix.db"))
        return None

    def _concrete(value: str) -> str:
        """Return a usable value, or '' if absent or an unresolved ${...} placeholder."""
        value = value.strip()
        return "" if (not value or "${" in value) else value

    # (1) explicit opt-in URL
    opt_url = _concrete(os.environ.get(_MATRIX_URL_ENV[dialect], ""))
    if opt_url:
        monkeypatch.setenv("CLOUD_DOG_DB__URL", opt_url)
        return None

    # (2) harness env file already configured this dialect with CONCRETE (Vault-resolved) values
    if snapshot["CLOUD_DOG_DB__DIALECT"].strip().lower() == dialect:
        url = _concrete(snapshot["CLOUD_DOG_DB__URL"])
        if url:
            monkeypatch.setenv("CLOUD_DOG_DB__URL", url)
            return None
        if _concrete(snapshot["CLOUD_DOG_DB__HOST"]):
            for key in _DB_ENV_KEYS:
                concrete = _concrete(snapshot[key])
                if concrete:
                    monkeypatch.setenv(key, concrete)
            return None
        return (
            f"{dialect} backend configured via env file but credentials are unresolved "
            f"(${{vault...}} placeholders need a Vault token not present in this run)"
        )

    return (
        f"{dialect} backend not configured (set {_MATRIX_URL_ENV[dialect]} to a disposable test DB URL, "
        f"or run with --env tests/env-DB-{'postgresql' if dialect == 'postgresql' else 'mysql'} and a Vault token)"
    )


def _round_trip(dialect: str) -> None:
    service = StructureService()
    bundle = StructureBundle(
        document=StructureDocument(
            profile_id="default",
            collection_id="matrix",
            source_hash=f"matrix-{dialect}",
            extractor_provider="manual",
        ),
        pages=[StructurePage(page_number=1)],
        sections=[StructureSection(section_id="s1", title="Intro", level=0)],
    )
    created = service.create(bundle, actor="matrix", roles={"admin"})
    sdid = created["document"]["structure_document_id"]
    assert service.get(sdid)["document"]["structure_document_id"] == sdid
    assert any(d["structure_document_id"] == sdid for d in service.list(collection_id="matrix")["documents"])
    assert service.list_pages(sdid)["count"] == 1
    assert service.delete(sdid, actor="matrix", roles={"admin"})["deleted"] is True
    with pytest.raises(KeyError):
        service.get(sdid)
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.req("FR-005")


@pytest.mark.parametrize("dialect", _DIALECTS)
def test_structure_backend_matrix_round_trip(monkeypatch, tmp_path, dialect: str) -> None:
    reason = _configure(monkeypatch, dialect, tmp_path)
    if reason:
        pytest.skip(reason)
    initialise_database(force_reinit=True)
    try:
        _round_trip(dialect)
    finally:
        shutdown_database()
