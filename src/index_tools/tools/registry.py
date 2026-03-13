# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# index-retriever-mcp-server — Tool Registry
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Registry of tool schemas and handlers.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from index_tools.tools.definitions import (
    ExtractOnlyOutput,
    GenericToolInput,
    GenericToolOutput,
    IngestOutput,
    IngestPreviewInput,
    IngestPreviewOutput,
    IngestTextInput,
    OcrRunInput,
    OcrRunOutput,
    ParsersListInput,
    ParsersListOutput,
    ParserTestInput,
    ParserTestOutput,
    SearchInput,
    SearchOutput,
    TableExtractOutput,
)


@dataclass(slots=True)
class ToolSpec:
    """ToolSpec definition."""

    name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]


class ToolRegistry:
    """Tool registry with schema lookup and listing support."""

    def __init__(self) -> None:
        """Initialise the instance state."""
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """Execute register."""
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        """Execute get."""
        return self._tools[name]

    def list_tools(self) -> list[dict[str, Any]]:
        """Execute list tools."""
        return [
            {
                "name": spec.name,
                "input_schema": spec.input_model.model_json_schema(),
                "output_schema": spec.output_model.model_json_schema(),
            }
            for spec in self._tools.values()
        ]


def build_default_tool_registry() -> ToolRegistry:
    """Execute build default tool registry."""
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
        ToolSpec(name="parsers_list", input_model=ParsersListInput, output_model=ParsersListOutput),
        ToolSpec(name="parser_test", input_model=ParserTestInput, output_model=ParserTestOutput),
        ToolSpec(name="ingest_preview", input_model=IngestPreviewInput, output_model=IngestPreviewOutput),
        ToolSpec(name="extract_only", input_model=IngestPreviewInput, output_model=ExtractOnlyOutput),
        ToolSpec(name="ocr_run", input_model=OcrRunInput, output_model=OcrRunOutput),
        ToolSpec(name="table_extract", input_model=IngestPreviewInput, output_model=TableExtractOutput),
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
