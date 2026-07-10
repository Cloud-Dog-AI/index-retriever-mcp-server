"""W28E-604 spreadsheet indexing control plane (Excel requirements §14)

Revision ID: 20260604_0004
Revises: 20260604_0003
Create Date: 2026-06-04 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260604_0004"
down_revision = "20260604_0003"
branch_labels = None
depends_on = None

_TS = sa.text("CURRENT_TIMESTAMP")


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_TS, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_TS, nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "ss_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_uri", sa.String(length=1024), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("last_seen_hash", sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ss_sources_uri_tenant", "ss_sources", ["source_uri", "tenant_id"], unique=True)

    op.create_table(
        "ss_index_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("stats_json", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["source_id"], ["ss_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ss_index_jobs_source_id", "ss_index_jobs", ["source_id"], unique=False)

    op.create_table(
        "ss_source_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("version_hash", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parser_version", sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["source_id"], ["ss_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ss_source_versions_source_id", "ss_source_versions", ["source_id"], unique=False)

    op.create_table(
        "ss_objects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_version_id", sa.Integer(), nullable=False),
        sa.Column("object_type", sa.String(length=32), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("parent_object_key", sa.String(length=512), nullable=False),
        sa.Column("sheet_name", sa.String(length=256), nullable=False),
        sa.Column("table_name", sa.String(length=256), nullable=False),
        sa.Column("range_ref", sa.String(length=64), nullable=False),
        sa.Column("object_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["source_version_id"], ["ss_source_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ss_objects_version", "ss_objects", ["source_version_id"], unique=False)
    op.create_index("ix_ss_objects_key", "ss_objects", ["object_key"], unique=False)

    op.create_table(
        "ss_extracted_tables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_version_id", sa.Integer(), nullable=False),
        sa.Column("object_id", sa.Integer(), nullable=False),
        sa.Column("sheet_name", sa.String(length=256), nullable=False),
        sa.Column("table_name", sa.String(length=256), nullable=False),
        sa.Column("range_ref", sa.String(length=64), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=False),
        sa.Column("storage_format", sa.String(length=32), nullable=False),
        sa.Column("storage_uri", sa.String(length=1024), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("column_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["source_version_id"], ["ss_source_versions.id"]),
        sa.ForeignKeyConstraint(["object_id"], ["ss_objects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ss_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("object_id", sa.Integer(), nullable=False),
        sa.Column("chunk_key", sa.String(length=512), nullable=False),
        sa.Column("backend_name", sa.String(length=64), nullable=False),
        sa.Column("backend_record_id", sa.String(length=512), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_profile", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["object_id"], ["ss_objects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ss_chunks_object_id", "ss_chunks", ["object_id"], unique=False)

    op.create_table(
        "ss_refresh_manifests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("previous_source_version_id", sa.Integer(), nullable=True),
        sa.Column("current_source_version_id", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("previous_object_hash", sa.String(length=64), nullable=False),
        sa.Column("current_object_hash", sa.String(length=64), nullable=False),
        sa.Column("refresh_action", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["source_id"], ["ss_sources.id"]),
        sa.ForeignKeyConstraint(["previous_source_version_id"], ["ss_source_versions.id"]),
        sa.ForeignKeyConstraint(["current_source_version_id"], ["ss_source_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ss_backend_sync_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_version_id", sa.Integer(), nullable=False),
        sa.Column("backend_name", sa.String(length=64), nullable=False),
        sa.Column("sync_status", sa.String(length=32), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_record_count", sa.Integer(), nullable=False),
        sa.Column("upserted_record_count", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["source_version_id"], ["ss_source_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ss_index_errors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["job_id"], ["ss_index_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ss_index_errors")
    op.drop_table("ss_backend_sync_state")
    op.drop_table("ss_refresh_manifests")
    op.drop_index("ix_ss_chunks_object_id", table_name="ss_chunks")
    op.drop_table("ss_chunks")
    op.drop_table("ss_extracted_tables")
    op.drop_index("ix_ss_objects_key", table_name="ss_objects")
    op.drop_index("ix_ss_objects_version", table_name="ss_objects")
    op.drop_table("ss_objects")
    op.drop_index("ix_ss_source_versions_source_id", table_name="ss_source_versions")
    op.drop_table("ss_source_versions")
    op.drop_index("ix_ss_index_jobs_source_id", table_name="ss_index_jobs")
    op.drop_table("ss_index_jobs")
    op.drop_index("ix_ss_sources_uri_tenant", table_name="ss_sources")
    op.drop_table("ss_sources")
