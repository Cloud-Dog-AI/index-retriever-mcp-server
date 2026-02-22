# index-retriever-mcp-server — Collection Schema
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Collection schema definitions.

from __future__ import annotations

from pydantic import BaseModel


class CollectionSchema(BaseModel):
    name: str
    dimension: int
    distance_metric: str = "cosine"
