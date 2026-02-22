# index-retriever-mcp-server — S3 Connector
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: S3 URI resolver for connector fetch planning.

from __future__ import annotations

from urllib.parse import urlparse

from index_tools.connectors.models import FetchPlan


def resolve(uri: str) -> FetchPlan:
    """Execute resolve."""
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError("Invalid S3 URI")
    key = parsed.path.lstrip("/")
    return FetchPlan(source_type="s3", location=uri, metadata={"bucket": parsed.netloc, "key": key})
