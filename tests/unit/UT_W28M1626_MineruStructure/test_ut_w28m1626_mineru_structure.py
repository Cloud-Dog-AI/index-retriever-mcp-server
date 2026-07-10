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

"""W28M-1626 unit tests — config-driven parser-service defaults + file/bytes
structure extraction.

Regression guard for the gap that made the prior "document-structure delivered"
claim hollow: the deployed service injected no default ``parser_services`` and the
MCP/REST ``structure_extract`` tool had no file path, so ``provider="mineru"``
could never run live on a real country-report PDF. These tests prove the MinerU
endpoint is now resolved from ``cloud_dog_config`` (no caller hardcoding) and that
``StructureService.extract_file`` routes bytes through the parser registry.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import cloud_dog_vdb.ingestion.pipeline as vdb_pipeline
from index_tools import parser_services as ps
from index_tools.db.runtime import initialise_database, shutdown_database
from index_tools.structure import StructureService


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
    ):
        monkeypatch.delenv(name, raising=False)


class _CapturingAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def log_admin_action(self, **kwargs) -> None:  # noqa: ANN003
        self.events.append(kwargs)


def _patch_config(monkeypatch, mapping: dict[str, str]) -> None:
    """Force ``cloud_dog_config.get_config`` to return only *mapping* values."""

    def _fake_get_config(key: str):  # noqa: ANN202
        return mapping.get(key)

    monkeypatch.setattr("cloud_dog_config.get_config", _fake_get_config, raising=False)


@pytest.fixture()
def structure_service(monkeypatch, tmp_path: Path):
    _configure_sqlite_env(monkeypatch, tmp_path / "w28m1626-ut.db")
    initialise_database(force_reinit=True)
    try:
        yield StructureService(audit_logger=_CapturingAudit())
    finally:
        shutdown_database()


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-007")
def test_default_parser_services_reads_mineru_from_config(monkeypatch) -> None:
    _patch_config(monkeypatch, {"index.parsers.mineru.base_url": "https://mineru.example/"})
    services = ps.default_parser_services()
    assert services["mineru"]["base_url"] == "https://mineru.example/"
    assert services["mineru"]["timeout_seconds"] == 120.0


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-007")
def test_default_parser_services_empty_without_config(monkeypatch) -> None:
    _patch_config(monkeypatch, {})
    assert ps.default_parser_services() == {}


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-007")
def test_merge_parser_services_caller_overrides_config(monkeypatch) -> None:
    _patch_config(monkeypatch, {"index.parsers.mineru.base_url": "https://cfg/"})
    merged = ps.merge_parser_services({"mineru": {"base_url": "https://caller/"}})
    assert merged["mineru"]["base_url"] == "https://caller/"
    # config-only providers still present when caller does not mention them
    _patch_config(monkeypatch, {"index.parsers.mineru.base_url": "https://cfg/"})
    assert ps.merge_parser_services(None)["mineru"]["base_url"] == "https://cfg/"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-007")
def test_extract_file_mineru_uses_config_default_endpoint(monkeypatch, structure_service) -> None:
    """extract_file(provider='mineru') with NO parser_services must build the registry
    with the MinerU endpoint taken from cloud_dog_config — proving the config default."""
    _patch_config(monkeypatch, {"index.parsers.mineru.base_url": "https://mineru.example/"})
    captured: dict[str, object] = {}

    def _fake_build(services=None):  # noqa: ANN202
        captured["services"] = services
        raise RuntimeError("registry-built-sentinel")

    monkeypatch.setattr(vdb_pipeline, "build_parser_registry", _fake_build)

    with pytest.raises(RuntimeError, match="registry-built-sentinel"):
        structure_service.extract_file(
            b"%PDF-1.4 fake",
            filename="report.pdf",
            mime_type="application/pdf",
            profile="p",
            collection="c",
            provider="mineru",
        )
    assert captured["services"]["mineru"]["base_url"] == "https://mineru.example/"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-007")
def test_parse_via_vdb_runs_inside_running_event_loop(monkeypatch) -> None:
    """The live-provider parse must succeed when invoked from inside a running event
    loop — the MCP/REST server dispatches tool handlers within the server loop, and
    the previous code raised 'must be called outside a running event loop' there."""
    from index_tools.structure import extract as ex

    class _FakeParser:
        async def parse_bytes(self, data, **kwargs):  # noqa: ANN001, ANN003
            return {"ir": "ok", "bytes": len(data)}

    class _FakeRegistry:
        def get(self, provider_id):  # noqa: ANN001
            return _FakeParser() if provider_id == "mineru" else None

    monkeypatch.setattr(vdb_pipeline, "build_parser_registry", lambda services=None: _FakeRegistry())

    import asyncio

    async def _call():
        # sync _parse_via_vdb invoked from within a running loop
        return ex._parse_via_vdb(
            b"abc", filename="f.pdf", mime_type="application/pdf",
            provider="mineru", parser_services={"mineru": {"base_url": "https://m/"}}, options=None,
        )

    ir = asyncio.run(_call())
    assert ir == {"ir": "ok", "bytes": 3}


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-007")
def test_extract_file_internal_persists_structure(structure_service) -> None:
    """The internal provider path decodes bytes as (markdown) text and persists a bundle."""
    result = structure_service.extract_file(
        b"# Country Report\n\nOverview text.\n\n## Governance\n\nDetail.\n",
        filename="report.md",
        mime_type="text/markdown",
        profile="p",
        collection="c",
        provider="internal",
    )
    document = result.get("document") or {}
    assert document.get("structure_document_id"), result.keys()
    # the two markdown headings become titled sections
    assert len(result.get("sections", [])) >= 2
