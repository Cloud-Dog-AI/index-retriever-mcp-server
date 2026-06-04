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

"""SQL control-plane models for spreadsheet indexing (Excel requirements §14).

These are the indexing control plane (sources, jobs, versions, object/chunk
manifests, refresh decisions, backend sync state, errors). They are owned by
index-retriever-mcp-server and built on ``cloud_dog_db`` (RULES §1.4 — the SQL
abstraction is never re-implemented). Tables are prefixed ``ss_`` to stay
collision-free in a shared database, and use portable column types so the same
models run on SQLite, MariaDB and PostgreSQL (§14.1).
"""

from __future__ import annotations

from datetime import datetime

from cloud_dog_db import PlatformBase, TimestampMixin
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class SpreadsheetSource(PlatformBase, TimestampMixin):
    """A registered source object (§14.2 sources)."""

    __tablename__ = "ss_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="excel")
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    last_seen_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class SpreadsheetIndexJob(PlatformBase, TimestampMixin):
    """An indexing run (§14.2 index_jobs)."""

    __tablename__ = "ss_index_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("ss_sources.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, default="index")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stats_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SpreadsheetSourceVersion(PlatformBase, TimestampMixin):
    """A workbook version (§14.2 source_versions)."""

    __tablename__ = "ss_source_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("ss_sources.id"), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    version_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class SpreadsheetObject(PlatformBase, TimestampMixin):
    """A canonical workbook object manifest entry (§14.2 objects)."""

    __tablename__ = "ss_objects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_version_id: Mapped[int] = mapped_column(ForeignKey("ss_source_versions.id"), nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    parent_object_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    sheet_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    table_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    range_ref: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    object_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SpreadsheetExtractedTable(PlatformBase, TimestampMixin):
    """An optional structured table/range extract (§14.2 extracted_tables)."""

    __tablename__ = "ss_extracted_tables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_version_id: Mapped[int] = mapped_column(ForeignKey("ss_source_versions.id"), nullable=False)
    object_id: Mapped[int] = mapped_column(ForeignKey("ss_objects.id"), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    table_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    range_ref: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    schema_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    storage_format: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class SpreadsheetChunk(PlatformBase, TimestampMixin):
    """An emitted searchable record manifest entry (§14.2 chunks)."""

    __tablename__ = "ss_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("ss_objects.id"), nullable=False)
    chunk_key: Mapped[str] = mapped_column(String(512), nullable=False)
    backend_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    backend_record_id: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    embedding_profile: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SpreadsheetRefreshManifest(PlatformBase, TimestampMixin):
    """An object-level refresh decision across versions (§14.2 refresh_manifests)."""

    __tablename__ = "ss_refresh_manifests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("ss_sources.id"), nullable=False)
    previous_source_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("ss_source_versions.id"), nullable=True
    )
    current_source_version_id: Mapped[int] = mapped_column(ForeignKey("ss_source_versions.id"), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    previous_object_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    current_object_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    refresh_action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(256), nullable=False, default="")


class SpreadsheetBackendSyncState(PlatformBase, TimestampMixin):
    """Backend sync and deletion state (§14.2 backend_sync_state)."""

    __tablename__ = "ss_backend_sync_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_version_id: Mapped[int] = mapped_column(ForeignKey("ss_source_versions.id"), nullable=False)
    backend_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    sync_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    upserted_record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SpreadsheetIndexError(PlatformBase, TimestampMixin):
    """A detailed warning or failure (§14.2 index_errors)."""

    __tablename__ = "ss_index_errors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("ss_index_jobs.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="warning")
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    object_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
