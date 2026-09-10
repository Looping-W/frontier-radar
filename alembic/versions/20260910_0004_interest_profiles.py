"""Create future-ready interest profiles and deterministic article rankings.

Revision ID: 20260910_0004
Revises: 20260904_0003
Create Date: 2026-09-10
"""

import sqlalchemy as sa

from alembic import op

revision = "20260910_0004"
down_revision = "20260904_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interest_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "interest_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("name_key", sa.String(length=512), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["interest_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "name_key"),
    )
    op.create_index(
        "ix_interest_topics_profile_id", "interest_topics", ["profile_id"], unique=False
    )
    op.create_table(
        "interest_keywords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("name_key", sa.String(length=512), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["interest_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "name_key"),
    )
    op.create_index(
        "ix_interest_keywords_profile_id",
        "interest_keywords",
        ["profile_id"],
        unique=False,
    )
    op.create_table(
        "article_rankings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["profile_id"], ["interest_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "article_id"),
    )
    op.create_index(
        "ix_article_rankings_profile_id",
        "article_rankings",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_article_rankings_article_id",
        "article_rankings",
        ["article_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_article_rankings_article_id", table_name="article_rankings")
    op.drop_index("ix_article_rankings_profile_id", table_name="article_rankings")
    op.drop_table("article_rankings")
    op.drop_index("ix_interest_keywords_profile_id", table_name="interest_keywords")
    op.drop_table("interest_keywords")
    op.drop_index("ix_interest_topics_profile_id", table_name="interest_topics")
    op.drop_table("interest_topics")
    op.drop_table("interest_profiles")
