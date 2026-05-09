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
from sqlalchemy import Column, MetaData, String, Table, select

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService


def _headers() -> dict[str, str]:
    return {"x-api-key": "test-api-key", "Authorization": "Bearer test-api-key"}


def test_it2_15_database_startup_and_crud(tmp_path) -> None:
    service = IndexService(audit_path=str(tmp_path / "audit-it2-15.jsonl"))
    try:
        app = build_api_app(service=service)
        runtime = app.state.db_runtime
        table_name = f"it2_15_db_{uuid4().hex[:8]}"
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
            payload = health.json()
            db_probe = (payload.get("checks") or {}).get("db") or {}
            assert bool(db_probe.get("ok")) is True

            metadata.create_all(runtime.engine)
            try:
                with runtime.engine.begin() as conn:
                    conn.execute(records.insert().values(id="row-1", value="alpha"))
                    row = conn.execute(select(records.c.value).where(records.c.id == "row-1")).scalar_one()
                assert row == "alpha"
            finally:
                metadata.drop_all(runtime.engine)
    finally:
        service.close()
