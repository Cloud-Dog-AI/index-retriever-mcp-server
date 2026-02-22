# index-retriever-mcp-server — Google Drive Connector
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Google Drive reference resolver for connector fetch planning.

from __future__ import annotations

from index_tools.connectors.models import FetchPlan


def resolve(file_id: str) -> FetchPlan:
    if not file_id.strip():
        raise ValueError("Google Drive file ID is required")
    return FetchPlan(source_type="gdrive", location=file_id, metadata={"file_id": file_id})
