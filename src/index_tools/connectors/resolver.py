# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""W28C-427 IDX-SNAG-004: Connector resolver for ingest_reference.

Routes source URIs to the appropriate connector module based on scheme.
"""

from __future__ import annotations

from urllib.parse import urlparse

from index_tools.connectors.models import FetchPlan

# Supported source types and their schemes.
SUPPORTED_SOURCE_TYPES = [
    "filesystem",
    "http",
    "s3",
    "webdav",
    "ftp",
    "gdrive",
]


def resolve_source(uri: str, *, allowed_roots: list[str] | None = None) -> FetchPlan:
    """Resolve a source URI to a FetchPlan using the appropriate connector.

    Raises ValueError if the scheme is not supported or the URI is malformed.
    """
    uri = uri.strip()
    if not uri:
        raise ValueError("Empty source URI")

    parsed = urlparse(uri)
    scheme = (parsed.scheme or "").lower()

    # Google Drive shared links use HTTPS, so detect them before generic HTTP.
    if scheme == "gdrive" or "drive.google.com" in uri or "docs.google.com" in uri:
        from index_tools.connectors.gdrive import resolve as gdrive_resolve
        return gdrive_resolve(uri)

    # HTTP/HTTPS
    if scheme in {"http", "https"}:
        from index_tools.connectors.http import resolve as http_resolve
        return http_resolve(uri)

    # Filesystem: no scheme or file:// scheme
    if not scheme or scheme == "file":
        from index_tools.connectors.filesystem import resolve as fs_resolve
        roots = allowed_roots or ["."]
        return fs_resolve(roots, uri.replace("file://", "", 1) if scheme == "file" else uri)

    # S3
    if scheme == "s3":
        from index_tools.connectors.s3 import resolve as s3_resolve
        return s3_resolve(uri)

    # WebDAV
    if scheme in {"webdav", "webdavs", "dav", "davs"}:
        from index_tools.connectors.webdav import resolve as webdav_resolve
        return webdav_resolve(uri)

    # FTP/FTPS
    if scheme in {"ftp", "ftps"}:
        from index_tools.connectors.ftp import resolve as ftp_resolve
        return ftp_resolve(uri)

    raise ValueError(f"Unsupported source scheme: {scheme!r}")


def fetch_source(plan: FetchPlan, *, timeout_seconds: float = 30.0) -> bytes:
    """Fetch content from a resolved FetchPlan.

    Uses the connector's fetch function if available, otherwise raises.
    """
    source_type = plan.source_type

    if source_type == "filesystem":
        from index_tools.connectors.filesystem import fetch as fs_fetch
        return fs_fetch(plan)

    if source_type == "http":
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(plan.location, method="GET")
        with urllib.request.urlopen(req, context=ctx, timeout=timeout_seconds) as resp:
            return resp.read()

    if source_type == "ftp":
        from index_tools.connectors.ftp import fetch as ftp_fetch
        return ftp_fetch(plan, timeout_seconds=timeout_seconds)

    if source_type in {"s3", "webdav", "gdrive"}:
        raise NotImplementedError(
            f"Fetch for {source_type} requires backend credentials; "
            f"use cloud_dog_storage or profile-specific fetch."
        )

    raise ValueError(f"No fetcher for source type: {source_type!r}")
