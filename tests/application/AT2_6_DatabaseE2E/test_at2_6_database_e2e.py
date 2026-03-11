# index-retriever-mcp-server — AT2.6 DatabaseE2E
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: End-to-end DB lifecycle (create/update/delete) with API runtime online.

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Column, MetaData, String, Table, select, update

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService


def _headers() -> dict[str, str]:
    return {"x-api-key": "test-api-key", "Authorization": "Bearer test-api-key"}


def test_at2_6_database_e2e(tmp_path) -> None:
    service = IndexService(audit_path=str(tmp_path / "audit-at2-6.jsonl"))
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
        health = client.get("/app/v1/health", headers=_headers())
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
