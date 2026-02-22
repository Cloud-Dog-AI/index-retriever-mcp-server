# index-retriever-mcp-server — FTP Connector
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: FTP URI resolver for connector fetch planning.

from __future__ import annotations

from urllib.parse import urlparse

from index_tools.connectors.models import FetchPlan


def resolve(uri: str) -> FetchPlan:
    parsed = urlparse(uri)
    if parsed.scheme not in {"ftp", "ftps"}:
        raise ValueError("Invalid FTP URI")
    return FetchPlan(source_type="ftp", location=uri, metadata={"host": parsed.netloc})
