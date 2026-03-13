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

# index-retriever-mcp-server — FTP Connector
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: FTP URI resolver for connector fetch planning.

from __future__ import annotations

from ftplib import FTP, all_errors as ftp_errors, error_perm
from urllib.parse import unquote
from urllib.parse import urlparse

from index_tools.connectors.models import FetchPlan


def resolve(uri: str) -> FetchPlan:
    """Execute resolve."""
    parsed = urlparse(uri)
    if parsed.scheme not in {"ftp", "ftps"} or not parsed.hostname:
        raise ValueError("Invalid FTP URI")
    path = unquote(parsed.path or "").lstrip("/")
    if not path:
        raise ValueError("FTP path is required")
    return FetchPlan(
        source_type="ftp",
        location=uri,
        metadata={
            "host": parsed.hostname,
            "port": str(parsed.port or 21),
            "path": path,
            "username": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
        },
    )


def fetch(plan: FetchPlan, timeout_seconds: float = 10.0) -> bytes:
    """Fetch remote FTP object and translate transport failures into domain errors."""
    host = plan.metadata.get("host", "").strip()
    path = plan.metadata.get("path", "").strip()
    if not host or not path:
        raise ValueError("FTP fetch plan missing host/path")
    port = int(plan.metadata.get("port", "21") or 21)
    username = plan.metadata.get("username", "").strip()
    password = plan.metadata.get("password", "")

    buffer = bytearray()
    try:
        with FTP() as client:
            client.connect(host=host, port=port, timeout=float(timeout_seconds))
            if username:
                client.login(user=username, passwd=password)
            else:
                client.login()
            client.retrbinary(f"RETR {path}", buffer.extend)
    except error_perm as exc:
        message = str(exc)
        if message.startswith("530"):
            raise PermissionError(f"FTP authentication failed for {host}") from exc
        if message.startswith("550"):
            raise FileNotFoundError(f"FTP file not found: {path}") from exc
        raise ConnectionError(f"FTP protocol error for {host}: {message}") from exc
    except ftp_errors as exc:
        raise ConnectionError(f"FTP connection failed for {host}:{port}") from exc

    return bytes(buffer)
