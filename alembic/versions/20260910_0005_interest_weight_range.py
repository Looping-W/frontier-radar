"""Constrain persisted interest weights to the one-to-five scale.

Revision ID: 20260910_0005
Revises: 20260910_0004
Create Date: 2026-09-10
"""

from alembic import op

revision = "20260910_0005"
down_revision = "20260910_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name, constraint_name in (
        ("interest_topics", "ck_interest_topics_weight_range"),
        ("interest_keywords", "ck_interest_keywords_weight_range"),
    ):
        op.execute(f"UPDATE {table_name} SET weight = 1 WHERE weight < 1")
        op.execute(f"UPDATE {table_name} SET weight = 5 WHERE weight > 5")
        op.create_check_constraint(
            constraint_name,
            table_name,
            "weight >= 1 AND weight <= 5",
        )


def downgrade() -> None:
    op.drop_constraint(
        "ck_interest_keywords_weight_range",
        "interest_keywords",
        type_="check",
    )
    op.drop_constraint(
        "ck_interest_topics_weight_range",
        "interest_topics",
        type_="check",
    )
