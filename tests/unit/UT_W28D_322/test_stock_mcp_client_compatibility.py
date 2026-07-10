# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from index_server import mcp_server
from index_server.auth.middleware import AuthResult


class _AllowAuth:
    def require_permission(self, _identity: AuthResult, _permission: str) -> None:
        return None

    def has_resource_binding(self, *_args: object, **_kwargs: object) -> bool:
        return False

    def authorise_resource(self, *_args: object, **_kwargs: object) -> bool:
        return True


class _FakeQueue:
    def __init__(self, status: str = "succeeded") -> None:
        self.status = status
        self.wait_calls: list[tuple[str, int | None]] = []

    def wait(self, job_id: str, timeout_seconds: int | None = None) -> dict[str, object]:
        self.wait_calls.append((job_id, timeout_seconds))
        return {
            "job_id": job_id,
            "status": self.status,
            "progress": {"phase": self.status, "percentage": 100},
        }


class _FakeService:
    def __init__(self, status: str = "succeeded") -> None:
        self.queue = _FakeQueue(status=status)
        self.ingest_text_calls: list[dict[str, object]] = []
        self.ingest_upload_calls: list[dict[str, object]] = []
        self.ingest_reference_calls: list[dict[str, object]] = []

    def ingest_text(self, **kwargs: object) -> str:
        self.ingest_text_calls.append(kwargs)
        return "text-job-1"

    def ingest_upload(self, **kwargs: object) -> dict[str, str]:
        self.ingest_upload_calls.append(kwargs)
        return {"job_id": "file-job-1"}

    def ingest_reference(self, **kwargs: object) -> str:
        self.ingest_reference_calls.append(kwargs)
        return "file-job-2"


def _identity() -> AuthResult:
    return AuthResult(
        user_id="writer",
        roles={"writer"},
        permissions=set(),
        token_type="direct",
    )


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-016")
def test_registry_advertises_ps95_stock_client_tools() -> None:
    registry = mcp_server.build_registry()
    names = mcp_server.list_tool_names(registry)

    assert "ingest_text" in names
    assert "ingest_text_long" in names
    assert "ingest_file_async" in names
    assert "ingest_file_async_blocking" in names


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-008")
def test_ingest_text_waits_and_returns_terminal_result() -> None:
    service = _FakeService()

    result = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "ingest_text",
        {"profile": "default", "collection": "docs", "text": "hello", "actor": "writer"},
        auth=_AllowAuth(),  # type: ignore[arg-type]
        identity=_identity(),
    )

    assert result["ok"] is True
    assert result["status"] == "succeeded"
    assert result["job_id"] == "text-job-1"
    assert result["poll_tool"] == "job_get"
    assert service.queue.wait_calls == [("text-job-1", 50)]


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-008")
def test_ingest_text_timeout_returns_structured_guidance() -> None:
    service = _FakeService(status="running")

    result = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "ingest_text_long",
        {"profile": "default", "collection": "docs", "text": "hello", "actor": "writer"},
        auth=_AllowAuth(),  # type: ignore[arg-type]
        identity=_identity(),
    )

    assert result["ok"] is False
    assert result["status"] == "running"
    assert result["error"]["code"] == -32000
    assert result["error"]["data"]["poll_tool"] == "job_get"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-008")
def test_ingest_file_async_and_blocking_contracts() -> None:
    service = _FakeService()

    async_result = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "ingest_file_async",
        {
            "profile": "default",
            "collection": "docs",
            "filename": "note.txt",
            "content": "file body",
            "actor": "writer",
        },
        auth=_AllowAuth(),  # type: ignore[arg-type]
        identity=_identity(),
    )

    assert async_result == {
        "ok": True,
        "job_id": "file-job-1",
        "status": "submitted",
        "poll_tool": "job_get",
        "blocking_tool": "ingest_file_async_blocking",
    }

    blocking_result = mcp_server.execute_tool(
        service,  # type: ignore[arg-type]
        "ingest_file_async_blocking",
        {
            "profile": "default",
            "collection": "docs",
            "uri": "file:///workspace/doc.txt",
            "actor": "writer",
        },
        auth=_AllowAuth(),  # type: ignore[arg-type]
        identity=_identity(),
    )

    assert blocking_result["ok"] is True
    assert blocking_result["status"] == "succeeded"
    assert blocking_result["job_id"] == "file-job-2"
    assert blocking_result["blocking_tool"] == "ingest_file_async_blocking"
