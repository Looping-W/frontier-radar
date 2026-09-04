"""Create raw API-response snapshots for Phase 1 collection.

Revision ID: 20260901_0002
Revises: 20260831_0001
Create Date: 2026-09-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "20260901_0002"
down_revision = "20260831_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("query", sa.String(length=512), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("raw_body", mysql.LONGTEXT(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_collection_snapshots_fetched_at",
        "collection_snapshots",
        ["fetched_at"],
        unique=False,
    )
    op.create_index(
        "ix_collection_snapshots_source",
        "collection_snapshots",
        ["source"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_collection_snapshots_source", table_name="collection_snapshots")
    op.drop_index(
        "ix_collection_snapshots_fetched_at",
        table_name="collection_snapshots",
    )
    op.drop_table("collection_snapshots")
