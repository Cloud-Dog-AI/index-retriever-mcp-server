# index-retriever-mcp-server — Tool Registry
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Registry of tool schemas and handlers.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from index_tools.tools.definitions import (
    GenericToolInput,
    GenericToolOutput,
    IngestOutput,
    IngestTextInput,
    SearchInput,
    SearchOutput,
)


@dataclass(slots=True)
class ToolSpec:
    name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]


class ToolRegistry:
    """Tool registry with schema lookup and listing support."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "input_schema": spec.input_model.model_json_schema(),
                "output_schema": spec.output_model.model_json_schema(),
            }
            for spec in self._tools.values()
        ]


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    specs: list[ToolSpec] = [
        ToolSpec(name="profiles_list", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="profile_get", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="admin_profile_create", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="admin_profile_update", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="admin_profile_delete", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="collections_list", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="collection_get", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="admin_collection_create", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="admin_collection_delete", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="ingest_upload", input_model=GenericToolInput, output_model=IngestOutput),
        ToolSpec(name="ingest_text", input_model=IngestTextInput, output_model=IngestOutput),
        ToolSpec(name="ingest_reference", input_model=GenericToolInput, output_model=IngestOutput),
        ToolSpec(name="ingest_stream_open", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="ingest_stream_event", input_model=GenericToolInput, output_model=IngestOutput),
        ToolSpec(name="ingest_stream_close", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="search", input_model=SearchInput, output_model=SearchOutput),
        ToolSpec(name="retrieve", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="search_explain", input_model=SearchInput, output_model=SearchOutput),
        ToolSpec(name="job_list", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="job_get", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="job_wait", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="job_stream", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="job_cancel", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="job_retry", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="queue_status", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="delete_by_id", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="delete_by_filter", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="retention_run", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="reindex_run", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="backend_health_check", input_model=GenericToolInput, output_model=GenericToolOutput),
        ToolSpec(name="embedding_health_check", input_model=GenericToolInput, output_model=GenericToolOutput),
    ]
    for spec in specs:
        registry.register(spec)
    return registry
