# index-retriever-mcp-server — WebDAV Connector
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: WebDAV URI resolver for connector fetch planning.

from __future__ import annotations

from urllib.parse import urlparse

from index_tools.connectors.models import FetchPlan


def resolve(uri: str) -> FetchPlan:
    parsed = urlparse(uri)
    if parsed.scheme not in {"webdav", "webdavs", "http", "https"}:
        raise ValueError("Invalid WebDAV URI")
    return FetchPlan(source_type="webdav", location=uri, metadata={"host": parsed.netloc})
