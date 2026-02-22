# index-retriever-mcp-server — Tool Definitions
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Pydantic input and output models for tool operations.

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    """SearchInput definition."""
    profile: str
    collection: str
    query: str
    top_k: int = 10
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """SearchResult definition."""
    doc_id: str
    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchOutput(BaseModel):
    """SearchOutput definition."""
    results: list[SearchResult] = Field(default_factory=list)


class IngestTextInput(BaseModel):
    """IngestTextInput definition."""
    profile: str
    collection: str
    text: str
    source: str = "inline"


class IngestOutput(BaseModel):
    """IngestOutput definition."""
    job_id: str
    status: str


class GenericToolInput(BaseModel):
    """GenericToolInput definition."""
    profile: str = "default"
    collection: str = "default"


class GenericToolOutput(BaseModel):
    """GenericToolOutput definition."""
    status: str = "ok"
