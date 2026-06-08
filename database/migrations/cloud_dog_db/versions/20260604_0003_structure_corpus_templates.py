"""index-retriever corpus + pattern + template tables (W28E-603 Phases 4/5)

Chains off the Phase-1 structure foundation.

Revision ID: 20260604_0003
Revises: 20260604_0002
Create Date: 2026-06-04 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260604_0003"
down_revision = "20260604_0002"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "structure_corpora",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("corpus_id", sa.String(length=128), nullable=False),
        sa.Column("profile_id", sa.String(length=128), nullable=False),
        sa.Column("collection_id", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ready"),
        sa.Column("document_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("corpus_id", name="uq_structure_corpora_cid"),
    )
    op.create_index("ix_structure_corpora_cid", "structure_corpora", ["corpus_id"], unique=False)
    op.create_index("ix_structure_corpora_profile", "structure_corpora", ["profile_id"], unique=False)
    op.create_index("ix_structure_corpora_collection", "structure_corpora", ["collection_id"], unique=False)
    op.create_index("ix_structure_corpora_status", "structure_corpora", ["status"], unique=False)

    op.create_table(
        "structure_patterns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pattern_id", sa.String(length=128), nullable=False),
        sa.Column("corpus_id", sa.String(length=128), nullable=False),
        sa.Column("pattern_type", sa.String(length=32), nullable=False, server_default="section"),
        sa.Column("signature", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("support_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_structure_patterns_pid", "structure_patterns", ["pattern_id"], unique=False)
    op.create_index("ix_structure_patterns_cid", "structure_patterns", ["corpus_id"], unique=False)
    op.create_index("ix_structure_patterns_type", "structure_patterns", ["pattern_type"], unique=False)

    op.create_table(
        "structure_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.String(length=128), nullable=False),
        sa.Column("corpus_id", sa.String(length=128), nullable=False),
        sa.Column("profile_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", name="uq_structure_templates_tid"),
    )
    op.create_index("ix_structure_templates_tid", "structure_templates", ["template_id"], unique=False)
    op.create_index("ix_structure_templates_cid", "structure_templates", ["corpus_id"], unique=False)
    op.create_index("ix_structure_templates_profile", "structure_templates", ["profile_id"], unique=False)


def downgrade() -> None:
    op.drop_table("structure_templates")
    op.drop_table("structure_patterns")
    op.drop_table("structure_corpora")
