"""Add profile-scoped article feedback and bounded learned adjustments.

Revision ID: 20260911_0007
Revises: 20260911_0006
Create Date: 2026-09-11
"""

import sqlalchemy as sa

from alembic import op

revision = "20260911_0007"
down_revision = "20260911_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interest_topics",
        sa.Column(
            "feedback_adjustment",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_interest_topics_feedback_adjustment_range",
        "interest_topics",
        "feedback_adjustment >= -2 AND feedback_adjustment <= 2",
    )
    op.add_column(
        "interest_keywords",
        sa.Column(
            "feedback_adjustment",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_interest_keywords_feedback_adjustment_range",
        "interest_keywords",
        "feedback_adjustment >= -2 AND feedback_adjustment <= 2",
    )
    op.create_table(
        "article_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('like', 'skip')", name="ck_article_feedback_decision"
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["profile_id"], ["interest_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "article_id"),
    )
    op.create_index(
        "ix_article_feedback_profile_id",
        "article_feedback",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_article_feedback_article_id",
        "article_feedback",
        ["article_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_article_feedback_article_id", table_name="article_feedback")
    op.drop_index("ix_article_feedback_profile_id", table_name="article_feedback")
    op.drop_table("article_feedback")
    op.drop_constraint(
        "ck_interest_keywords_feedback_adjustment_range",
        "interest_keywords",
        type_="check",
    )
    op.drop_column("interest_keywords", "feedback_adjustment")
    op.drop_constraint(
        "ck_interest_topics_feedback_adjustment_range",
        "interest_topics",
        type_="check",
    )
    op.drop_column("interest_topics", "feedback_adjustment")
