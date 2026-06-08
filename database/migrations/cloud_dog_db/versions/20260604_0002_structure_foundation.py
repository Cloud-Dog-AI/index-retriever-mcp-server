"""index-retriever-mcp-server document structure foundation (W28E-603 Phase 1)

Creates the canonical document-structure tables (design brief §6, §7.1) persisted through
cloud_dog_db. Chains off the platform baseline.

Revision ID: 20260604_0002
Revises: 20260305_0001
Create Date: 2026-06-04 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260604_0002"
down_revision = "20260305_0001"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "structure_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("structure_document_id", sa.String(length=128), nullable=False),
        sa.Column("profile_id", sa.String(length=128), nullable=False),
        sa.Column("collection_id", sa.String(length=128), nullable=False),
        sa.Column("source_document_id", sa.String(length=128), nullable=True),
        sa.Column("file_id", sa.String(length=128), nullable=True),
        sa.Column("source_hash", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("extractor_provider", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("schema_version", sa.String(length=32), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="complete"),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("structure_document_id", name="uq_structure_documents_sdid"),
    )
    op.create_index("ix_structure_documents_sdid", "structure_documents", ["structure_document_id"], unique=False)
    op.create_index("ix_structure_documents_profile", "structure_documents", ["profile_id"], unique=False)
    op.create_index("ix_structure_documents_collection", "structure_documents", ["collection_id"], unique=False)
    op.create_index("ix_structure_documents_source_doc", "structure_documents", ["source_document_id"], unique=False)
    op.create_index("ix_structure_documents_source_hash", "structure_documents", ["source_hash"], unique=False)
    op.create_index("ix_structure_documents_status", "structure_documents", ["status"], unique=False)

    op.create_table(
        "structure_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("page_id", sa.String(length=128), nullable=False),
        sa.Column("structure_document_id", sa.String(length=128), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_structure_pages_pid", "structure_pages", ["page_id"], unique=False)
    op.create_index("ix_structure_pages_sdid", "structure_pages", ["structure_document_id"], unique=False)
    op.create_index("ix_structure_pages_number", "structure_pages", ["page_number"], unique=False)

    op.create_table(
        "structure_blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.String(length=128), nullable=False),
        sa.Column("structure_document_id", sa.String(length=128), nullable=False),
        sa.Column("page_id", sa.String(length=128), nullable=True),
        sa.Column("section_id", sa.String(length=128), nullable=True),
        sa.Column("block_type", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("reading_order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_structure_blocks_bid", "structure_blocks", ["block_id"], unique=False)
    op.create_index("ix_structure_blocks_sdid", "structure_blocks", ["structure_document_id"], unique=False)
    op.create_index("ix_structure_blocks_page", "structure_blocks", ["page_id"], unique=False)
    op.create_index("ix_structure_blocks_section", "structure_blocks", ["section_id"], unique=False)

    op.create_table(
        "structure_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.String(length=128), nullable=False),
        sa.Column("structure_document_id", sa.String(length=128), nullable=False),
        sa.Column("parent_section_id", sa.String(length=128), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("section_type", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_structure_sections_secid", "structure_sections", ["section_id"], unique=False)
    op.create_index("ix_structure_sections_sdid", "structure_sections", ["structure_document_id"], unique=False)
    op.create_index("ix_structure_sections_parent", "structure_sections", ["parent_section_id"], unique=False)

    op.create_table(
        "structure_styles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.String(length=128), nullable=False),
        sa.Column("structure_document_id", sa.String(length=128), nullable=False),
        sa.Column("style_class", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_structure_styles_styid", "structure_styles", ["style_id"], unique=False)
    op.create_index("ix_structure_styles_sdid", "structure_styles", ["structure_document_id"], unique=False)

    op.create_table(
        "structure_tables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.String(length=128), nullable=False),
        sa.Column("structure_document_id", sa.String(length=128), nullable=False),
        sa.Column("page_id", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_structure_tables_tid", "structure_tables", ["table_id"], unique=False)
    op.create_index("ix_structure_tables_sdid", "structure_tables", ["structure_document_id"], unique=False)
    op.create_index("ix_structure_tables_page", "structure_tables", ["page_id"], unique=False)

    op.create_table(
        "structure_figures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("figure_id", sa.String(length=128), nullable=False),
        sa.Column("structure_document_id", sa.String(length=128), nullable=False),
        sa.Column("page_id", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_structure_figures_fid", "structure_figures", ["figure_id"], unique=False)
    op.create_index("ix_structure_figures_sdid", "structure_figures", ["structure_document_id"], unique=False)
    op.create_index("ix_structure_figures_page", "structure_figures", ["page_id"], unique=False)

    op.create_table(
        "structure_relations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("relation_id", sa.String(length=128), nullable=False),
        sa.Column("structure_document_id", sa.String(length=128), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("source_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("target_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_structure_relations_rid", "structure_relations", ["relation_id"], unique=False)
    op.create_index("ix_structure_relations_sdid", "structure_relations", ["structure_document_id"], unique=False)

    op.create_table(
        "structure_extractor_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("extractor_run_id", sa.String(length=128), nullable=False),
        sa.Column("structure_document_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="complete"),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_structure_runs_rid", "structure_extractor_runs", ["extractor_run_id"], unique=False)
    op.create_index("ix_structure_runs_sdid", "structure_extractor_runs", ["structure_document_id"], unique=False)


def downgrade() -> None:
    for table in (
        "structure_extractor_runs",
        "structure_relations",
        "structure_figures",
        "structure_tables",
        "structure_styles",
        "structure_sections",
        "structure_blocks",
        "structure_pages",
        "structure_documents",
    ):
        op.drop_table(table)
