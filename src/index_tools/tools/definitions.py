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


class ParsersListInput(BaseModel):
    """ParsersListInput definition."""
    parser_services: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ParsersListOutput(BaseModel):
    """ParsersListOutput definition."""
    parsers: list[dict[str, Any]] = Field(default_factory=list)


class ParserTestInput(BaseModel):
    """ParserTestInput definition."""
    provider_id: str
    sample_text: str = "parser health check"
    source_uri: str = "inline://parser-test.txt"
    parser_services: dict[str, dict[str, Any]] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class ParserTestOutput(BaseModel):
    """ParserTestOutput definition."""
    provider_id: str
    provider_version: str
    healthy: bool
    text_blocks: int
    table_blocks: int
    quality: dict[str, Any] = Field(default_factory=dict)


class IngestPreviewInput(BaseModel):
    """IngestPreviewInput definition."""
    text: str
    source_uri: str = "inline://preview.txt"
    parser_chain: list[str] = Field(default_factory=lambda: ["internal"])
    parser_options: dict[str, dict[str, Any]] = Field(default_factory=dict)
    parser_services: dict[str, dict[str, Any]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    ocr_mode: str = "disabled"
    ocr_provider: str = ""
    table_policy: str = "table_as_markdown"
    table_json_shape: str = "records"


class IngestPreviewOutput(BaseModel):
    """IngestPreviewOutput definition."""
    source_uri: str
    filename: str
    mime_type: str
    chunk_count: int
    parser_provider: str = ""
    parser_version: str = ""
    ocr_mode: str = "disabled"
    ocr_applied: bool = False
    table_policy: str = "table_as_markdown"
    checkpoints: list[dict[str, Any]] = Field(default_factory=list)


class ExtractOnlyOutput(BaseModel):
    """ExtractOnlyOutput definition."""
    source_uri: str
    text: str
    chunk_count: int
    parser_provider: str = ""
    ocr_applied: bool = False
    table_policy: str = "table_as_markdown"


class OcrRunInput(BaseModel):
    """OcrRunInput definition."""
    text: str
    mode: str = "auto"
    provider_id: str = ""
    min_chars: int = 200
    min_scanned_ratio: float = 0.5
    scanned_ratio: float = 0.0


class OcrRunOutput(BaseModel):
    """OcrRunOutput definition."""
    enabled: bool
    mode: str
    reason: str
    provider_id: str = ""


class TableExtractOutput(BaseModel):
    """TableExtractOutput definition."""
    source_uri: str
    table_policy: str
    table_json_shape: str
    table_count: int
    tables: list[str] = Field(default_factory=list)
    parser_provider: str = ""


class GenericToolInput(BaseModel):
    """GenericToolInput definition."""
    profile: str = "default"
    collection: str = "default"


class GenericToolOutput(BaseModel):
    """GenericToolOutput definition."""
    status: str = "ok"
