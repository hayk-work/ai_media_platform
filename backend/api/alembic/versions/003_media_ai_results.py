"""Add media AI analysis results table.

Revision ID: 003
Revises: 002
Create Date: 2026-06-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: str | Sequence[str] | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ai_analysis_status = postgresql.ENUM(
    "PENDING",
    "COMPLETED",
    "FAILED",
    name="ai_analysis_status",
    create_type=False,
)


def upgrade() -> None:
    ai_analysis_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "media_ai_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("media_item_id", sa.UUID(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(length=128)), nullable=False),
        sa.Column("labels", postgresql.ARRAY(sa.String(length=128)), nullable=False),
        sa.Column("quality_issues", postgresql.ARRAY(sa.String(length=256)), nullable=False),
        sa.Column("is_safe", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("status", ai_analysis_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["media_item_id"], ["media_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_item_id"),
    )


def downgrade() -> None:
    op.drop_table("media_ai_results")
    ai_analysis_status.drop(op.get_bind(), checkfirst=True)
