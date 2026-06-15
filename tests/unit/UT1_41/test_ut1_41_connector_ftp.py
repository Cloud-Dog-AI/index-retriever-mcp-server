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

import pytest

from index_tools.connectors import ftp
from index_tools.connectors.models import FetchPlan
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_connector_ftp_resolve_parses_uri() -> None:
    plan = ftp.resolve("ftp://alice:secret@example.com:2121/reports/daily.csv")
    assert plan.source_type == "ftp"
    assert plan.metadata["host"] == "example.com"
    assert plan.metadata["port"] == "2121"
    assert plan.metadata["path"] == "reports/daily.csv"
    assert plan.metadata["username"] == "alice"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_connector_ftp_resolve_rejects_invalid_uri() -> None:
    with pytest.raises(ValueError, match="Invalid FTP URI"):
        _ = ftp.resolve("https://example.com/reports/daily.csv")
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_connector_ftp_fetch_connection_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FailConnect:
        def __enter__(self) -> "_FailConnect":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            _ = exc_type, exc, tb
            return False

        def connect(self, host: str, port: int, timeout: float) -> None:
            _ = host, port, timeout
            raise OSError("connection refused")

    monkeypatch.setattr(ftp, "FTP", _FailConnect)
    plan = FetchPlan(source_type="ftp", location="ftp://example.com/file.txt", metadata={"host": "example.com", "path": "file.txt"})
    with pytest.raises(ConnectionError, match="FTP connection failed"):
        _ = ftp.fetch(plan)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_connector_ftp_fetch_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FailAuth:
        def __enter__(self) -> "_FailAuth":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            _ = exc_type, exc, tb
            return False

        def connect(self, host: str, port: int, timeout: float) -> None:
            _ = host, port, timeout

        def login(self, user: str = "", passwd: str = "") -> None:
            _ = user, passwd
            raise ftp.error_perm("530 Login incorrect")

    monkeypatch.setattr(ftp, "FTP", _FailAuth)
    plan = FetchPlan(
        source_type="ftp",
        location="ftp://alice@example.com/file.txt",
        metadata={"host": "example.com", "path": "file.txt", "username": "alice", "password": "bad"},
    )
    with pytest.raises(PermissionError, match="FTP authentication failed"):
        _ = ftp.fetch(plan)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_connector_ftp_fetch_file_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    class _MissingFile:
        def __enter__(self) -> "_MissingFile":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            _ = exc_type, exc, tb
            return False

        def connect(self, host: str, port: int, timeout: float) -> None:
            _ = host, port, timeout

        def login(self, user: str = "", passwd: str = "") -> None:
            _ = user, passwd

        def retrbinary(self, command: str, callback: object) -> None:
            _ = command, callback
            raise ftp.error_perm("550 File unavailable")

    monkeypatch.setattr(ftp, "FTP", _MissingFile)
    plan = FetchPlan(source_type="ftp", location="ftp://example.com/missing.txt", metadata={"host": "example.com", "path": "missing.txt"})
    with pytest.raises(FileNotFoundError, match="FTP file not found"):
        _ = ftp.fetch(plan)
