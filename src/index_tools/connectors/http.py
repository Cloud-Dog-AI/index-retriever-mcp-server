# index-retriever-mcp-server — HTTP Connector
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: HTTP URI resolver for optional web ingestion.

from __future__ import annotations

from urllib.parse import urlparse

from index_tools.connectors.models import FetchPlan


def resolve(uri: str) -> FetchPlan:
    parsed = urlparse(uri)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Invalid HTTP URI")
    return FetchPlan(source_type="http", location=uri, metadata={"host": parsed.netloc})
