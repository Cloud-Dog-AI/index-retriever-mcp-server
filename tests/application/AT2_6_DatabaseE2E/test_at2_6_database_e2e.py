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

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Column, MetaData, String, Table, select, update

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService
import pytest


def _headers() -> dict[str, str]:
    return {"x-api-key": "test-api-key", "Authorization": "Bearer test-api-key"}
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.req("FR-004")


def test_at2_6_database_e2e(tmp_path) -> None:
    service = IndexService(audit_path=str(tmp_path / "audit-at2-6.jsonl"))
    try:
        app = build_api_app(service=service)
        runtime = app.state.db_runtime
        table_name = f"at2_6_db_{uuid4().hex[:8]}"
        metadata = MetaData()
        records = Table(
            table_name,
            metadata,
            Column("id", String(64), primary_key=True),
            Column("value", String(128), nullable=False),
        )

        with TestClient(app) as client:
            health = client.get("/api/v1/health", headers=_headers())
            assert health.status_code == 200
            db_probe = (health.json().get("checks") or {}).get("db") or {}
            assert bool(db_probe.get("ok")) is True

            metadata.create_all(runtime.engine)
            try:
                with runtime.engine.begin() as conn:
                    conn.execute(records.insert().values(id="row-1", value="one"))
                    conn.execute(records.insert().values(id="row-2", value="two"))
                    conn.execute(update(records).where(records.c.id == "row-2").values(value="two-updated"))
                    values = list(conn.execute(select(records.c.id, records.c.value)))
                    assert len(values) == 2
                    assert any(row.id == "row-2" and row.value == "two-updated" for row in values)
                    conn.execute(records.delete().where(records.c.id == "row-1"))
                    remaining = list(conn.execute(select(records.c.id)))
                    assert [row.id for row in remaining] == ["row-2"]
            finally:
                metadata.drop_all(runtime.engine)
    finally:
        service.close()
