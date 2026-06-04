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

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from index_tools.tools.definitions import (
    BackendHealthOutput,
    EmbeddingHealthOutput,
    ExtractOnlyOutput,
    GenericToolInput,
    GenericToolOutput,
    IngestOutput,
    IngestReferenceInput,
    IngestPreviewInput,
    IngestPreviewOutput,
    IngestTextInput,
    LifecycleEvidenceInput,
    OcrRunInput,
    OcrRunOutput,
    ParsersListInput,
    ParsersListOutput,
    ParserTestInput,
    ParserTestOutput,
    RetrieveInput,
    RetrieveOutput,
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
    description: str = ""
    handler: str = ""


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
                "description": spec.description,
                "handler": spec.handler or spec.name,
                "input_schema": spec.input_model.model_json_schema(),
                "output_schema": spec.output_model.model_json_schema(),
            }
            for spec in self._tools.values()
        ]


def build_default_tool_registry() -> ToolRegistry:
    """Execute build default tool registry."""
    registry = ToolRegistry()
    specs: list[ToolSpec] = [
        # -- Profiles --
        ToolSpec(name="profiles_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List all configured profiles with their embedding and backend settings."),
        ToolSpec(name="profile_get", input_model=GenericToolInput, output_model=GenericToolOutput, description="Retrieve a single profile by its identifier."),
        ToolSpec(name="admin_profile_create", input_model=GenericToolInput, output_model=GenericToolOutput, description="Create a new profile with embedding model and backend configuration."),
        ToolSpec(name="admin_profile_update", input_model=GenericToolInput, output_model=GenericToolOutput, description="Update an existing profile's settings."),
        ToolSpec(name="admin_profile_delete", input_model=GenericToolInput, output_model=GenericToolOutput, description="Delete a profile and its associated configuration."),
        # -- Users --
        ToolSpec(name="users_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List all registered users with their roles and group memberships."),
        ToolSpec(name="user_get", input_model=GenericToolInput, output_model=GenericToolOutput, description="Retrieve a single user record by user ID."),
        ToolSpec(name="admin_user_create", input_model=GenericToolInput, output_model=GenericToolOutput, description="Create a new user with specified roles and group memberships."),
        ToolSpec(name="admin_user_update", input_model=GenericToolInput, output_model=GenericToolOutput, description="Update an existing user's display name, roles, or groups."),
        ToolSpec(name="admin_user_delete", input_model=GenericToolInput, output_model=GenericToolOutput, description="Delete a user and revoke their access."),
        # -- Groups --
        ToolSpec(name="groups_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List all groups with their roles and member lists."),
        ToolSpec(name="group_get", input_model=GenericToolInput, output_model=GenericToolOutput, description="Retrieve a single group by group ID."),
        ToolSpec(name="admin_group_create", input_model=GenericToolInput, output_model=GenericToolOutput, description="Create a new group with specified roles and members."),
        ToolSpec(name="admin_group_update", input_model=GenericToolInput, output_model=GenericToolOutput, description="Update a group's roles or membership list."),
        ToolSpec(name="admin_group_delete", input_model=GenericToolInput, output_model=GenericToolOutput, description="Delete a group."),
        # -- API Keys --
        ToolSpec(name="api_keys_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List all API keys with their labels, roles, and revocation status."),
        ToolSpec(name="admin_api_key_create", input_model=GenericToolInput, output_model=GenericToolOutput, description="Create a new API key bound to a user with specified roles."),
        ToolSpec(name="admin_api_key_revoke", input_model=GenericToolInput, output_model=GenericToolOutput, description="Revoke an API key, immediately disabling its access."),
        # -- A2A Events --
        ToolSpec(name="a2a_config_events", input_model=GenericToolInput, output_model=GenericToolOutput, description="Retrieve the log of admin configuration change events for A2A consumers."),
        # -- Collections --
        ToolSpec(name="collections_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List all collections, optionally filtered by profile."),
        ToolSpec(name="list_collections", input_model=GenericToolInput, output_model=GenericToolOutput, description="List all collections, optionally filtered by profile."),
        ToolSpec(name="collection_get", input_model=GenericToolInput, output_model=GenericToolOutput, description="Retrieve a single collection's metadata, dimensions, and access roles."),
        ToolSpec(name="admin_collection_create", input_model=GenericToolInput, output_model=GenericToolOutput, description="Create a new vector collection within a profile."),
        ToolSpec(name="admin_collection_update", input_model=GenericToolInput, output_model=GenericToolOutput, description="Update a collection's description, metadata, or access roles."),
        ToolSpec(name="admin_collection_delete", input_model=GenericToolInput, output_model=GenericToolOutput, description="Delete a collection and its stored vectors."),
        # -- Source Configs --
        ToolSpec(name="source_configs_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List all source configurations for connectors and ingestion schedules."),
        ToolSpec(name="source_config_get", input_model=GenericToolInput, output_model=GenericToolOutput, description="Retrieve a single source configuration by its ID."),
        ToolSpec(name="admin_source_config_create", input_model=GenericToolInput, output_model=GenericToolOutput, description="Create a new source configuration with URI, schedule, and metadata."),
        ToolSpec(name="admin_source_config_update", input_model=GenericToolInput, output_model=GenericToolOutput, description="Update an existing source configuration."),
        ToolSpec(name="admin_source_config_delete", input_model=GenericToolInput, output_model=GenericToolOutput, description="Delete a source configuration."),
        # -- RBAC --
        ToolSpec(name="rbac_bindings_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List all RBAC role bindings for users and groups."),
        ToolSpec(name="admin_rbac_bind", input_model=GenericToolInput, output_model=GenericToolOutput, description="Bind a role to a user or group entity."),
        ToolSpec(name="admin_rbac_unbind", input_model=GenericToolInput, output_model=GenericToolOutput, description="Remove a role binding from a user or group entity."),
        # -- Ingest --
        ToolSpec(name="ingest_upload", input_model=GenericToolInput, output_model=IngestOutput, description="Upload a file for chunking, embedding, and indexing into a collection."),
        ToolSpec(name="ingest_text", input_model=IngestTextInput, output_model=IngestOutput, description="Ingest inline text content into a profile and collection."),
        ToolSpec(name="ingest_reference", input_model=IngestReferenceInput, output_model=IngestOutput, description="Ingest content from a URI reference via a configured connector."),
        ToolSpec(name="parsers_list", input_model=ParsersListInput, output_model=ParsersListOutput, description="List available document parsers and their supported MIME types."),
        ToolSpec(name="parser_test", input_model=ParserTestInput, output_model=ParserTestOutput, description="Test a parser against sample content and return extraction results."),
        ToolSpec(name="ingest_preview", input_model=IngestPreviewInput, output_model=IngestPreviewOutput, description="Preview how content will be chunked and embedded without persisting."),
        ToolSpec(name="extract_only", input_model=IngestPreviewInput, output_model=ExtractOnlyOutput, description="Extract text and metadata from a document without chunking or indexing."),
        ToolSpec(name="ocr_run", input_model=OcrRunInput, output_model=OcrRunOutput, description="Run OCR on an image or scanned document and return extracted text."),
        ToolSpec(name="table_extract", input_model=IngestPreviewInput, output_model=TableExtractOutput, description="Extract structured table data from a document."),
        ToolSpec(name="ingest_stream_open", input_model=GenericToolInput, output_model=GenericToolOutput, description="Open a streaming ingestion session for incremental content delivery."),
        ToolSpec(name="ingest_stream_event", input_model=GenericToolInput, output_model=IngestOutput, description="Send a content event to an open streaming ingestion session."),
        ToolSpec(name="ingest_stream_close", input_model=GenericToolInput, output_model=GenericToolOutput, description="Close a streaming ingestion session and finalise indexing."),
        # -- Search --
        ToolSpec(name="search", input_model=SearchInput, output_model=SearchOutput, description="Perform a semantic vector search within a profile and collection."),
        # Covers: FR-P002
        ToolSpec(name="retrieve", input_model=RetrieveInput, output_model=RetrieveOutput, description="Retrieve a specific document by ID from a profile and collection."),
        ToolSpec(name="search_explain", input_model=SearchInput, output_model=SearchOutput, description="Perform a search with scoring explanation and relevance breakdown."),
        # -- Jobs --
        ToolSpec(name="job_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List all jobs with their current status and metadata."),
        ToolSpec(name="job_get", input_model=GenericToolInput, output_model=GenericToolOutput, description="Retrieve a single job's status, progress, and result."),
        ToolSpec(name="job_wait", input_model=GenericToolInput, output_model=GenericToolOutput, description="Block until a job completes or times out, then return its result."),
        ToolSpec(name="job_stream", input_model=GenericToolInput, output_model=GenericToolOutput, description="Stream real-time progress events from a running job."),
        ToolSpec(name="job_cancel", input_model=GenericToolInput, output_model=GenericToolOutput, description="Cancel a queued or running job."),
        ToolSpec(name="job_retry", input_model=GenericToolInput, output_model=GenericToolOutput, description="Retry a failed or cancelled job with the same parameters."),
        ToolSpec(name="job_delete", input_model=GenericToolInput, output_model=GenericToolOutput, description="Delete a terminal job record."),
        ToolSpec(name="queue_status", input_model=GenericToolInput, output_model=GenericToolOutput, description="Return queue depth, running job count, and backend health status."),
        ToolSpec(name="w28a_693_lifecycle_job", input_model=LifecycleEvidenceInput, output_model=GenericToolOutput, description="Create a source-backed W28A-693 lifecycle evidence job through the index-retriever queue runtime."),
        # -- Deletion & Lifecycle --
        ToolSpec(name="delete_by_id", input_model=GenericToolInput, output_model=GenericToolOutput, description="Delete a specific document from a collection by its ID."),
        ToolSpec(name="delete_by_filter", input_model=GenericToolInput, output_model=GenericToolOutput, description="Delete documents matching a metadata filter from a collection."),
        ToolSpec(name="retention_run", input_model=GenericToolInput, output_model=GenericToolOutput, description="Execute retention policy to remove expired or stale documents."),
        ToolSpec(name="reindex_run", input_model=GenericToolInput, output_model=GenericToolOutput, description="Re-embed and re-index existing documents in a collection."),
        # -- Health --
        ToolSpec(name="backend_health_check", input_model=GenericToolInput, output_model=BackendHealthOutput, description="Check connectivity and health of the vector database backend."),
        ToolSpec(name="embedding_health_check", input_model=GenericToolInput, output_model=EmbeddingHealthOutput, description="Check connectivity and health of the embedding model provider."),
        ToolSpec(name="ingest_health", input_model=GenericToolInput, output_model=GenericToolOutput, description="Return per-profile ingest pipeline health: queue depth, concurrency slots, embedder warm status, and last ingest latency."),
        # -- PS-78 File Lifecycle (W28C-427 IDX-SNAG-002) --
        ToolSpec(name="file_upload", input_model=GenericToolInput, output_model=GenericToolOutput, description="Upload a file to service storage. Returns file_id and metadata."),
        ToolSpec(name="file_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List stored files with optional profile/collection filter."),
        ToolSpec(name="file_get", input_model=GenericToolInput, output_model=GenericToolOutput, description="Get metadata for a stored file by ID."),
        ToolSpec(name="file_download", input_model=GenericToolInput, output_model=GenericToolOutput, description="Download stored file content by ID. Returns base64-encoded content."),
        ToolSpec(name="file_delete", input_model=GenericToolInput, output_model=GenericToolOutput, description="Delete a stored file by ID."),
        # -- W28E-603 Document Structure (Phase 1: model & persistence foundation) --
        ToolSpec(name="structure_health", input_model=GenericToolInput, output_model=GenericToolOutput, description="Report document-structure subsystem health, including the canonical structure store probe."),
        ToolSpec(name="structure_document_create", input_model=GenericToolInput, output_model=GenericToolOutput, description="Create or idempotently replace a canonical document-structure record (document plus pages/blocks/sections/styles/tables/figures/relations)."),
        ToolSpec(name="structure_document_get", input_model=GenericToolInput, output_model=GenericToolOutput, description="Retrieve a canonical structure document by its structure_document_id, optionally including child objects."),
        ToolSpec(name="structure_document_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List canonical structure documents, filtered by profile, collection or status, with pagination."),
        ToolSpec(name="structure_document_delete", input_model=GenericToolInput, output_model=GenericToolOutput, description="Delete a canonical structure document and all of its child objects."),
        ToolSpec(name="structure_outline_get", input_model=GenericToolInput, output_model=GenericToolOutput, description="Return the section hierarchy (outline) for a structure document as a nested tree."),
        ToolSpec(name="structure_pages_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List page-level layout records for a structure document."),
        ToolSpec(name="structure_sections_list", input_model=GenericToolInput, output_model=GenericToolOutput, description="List section records for a structure document."),
    ]
    for spec in specs:
        registry.register(spec)
    return registry
