"""Create normalized articles and traceable parsed raw items.

Revision ID: 20260904_0003
Revises: 20260901_0002
Create Date: 2026-09-04
"""

import sqlalchemy as sa

from alembic import op

revision = "20260904_0003"
down_revision = "20260901_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("title_key", sa.String(length=512), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_articles_title_key", "articles", ["title_key"], unique=False)
    op.create_index(
        "ix_articles_normalized_url",
        "articles",
        ["normalized_url"],
        unique=False,
        mysql_length=768,
    )

    op.create_table(
        "raw_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_item_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("normalized_url", sa.String(length=2048), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["collection_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "source_item_id"),
    )
    op.create_index(
        "ix_raw_items_article_id", "raw_items", ["article_id"], unique=False
    )
    op.create_index(
        "ix_raw_items_normalized_url",
        "raw_items",
        ["normalized_url"],
        unique=False,
        mysql_length=768,
    )
    op.create_index(
        "ix_raw_items_snapshot_id", "raw_items", ["snapshot_id"], unique=False
    )
    op.create_index("ix_raw_items_source", "raw_items", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_raw_items_source", table_name="raw_items")
    op.drop_index("ix_raw_items_snapshot_id", table_name="raw_items")
    op.drop_index("ix_raw_items_normalized_url", table_name="raw_items")
    op.drop_index("ix_raw_items_article_id", table_name="raw_items")
    op.drop_table("raw_items")
    op.drop_index("ix_articles_normalized_url", table_name="articles")
    op.drop_index("ix_articles_title_key", table_name="articles")
    op.drop_table("articles")
