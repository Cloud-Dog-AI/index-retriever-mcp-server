# index-retriever-mcp-server — Connector Models
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Data models shared by source connectors.

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class FetchPlan:
    """FetchPlan definition."""

    source_type: str
    location: str
    metadata: dict[str, str] = field(default_factory=dict)
