"""Create non-secret model configuration storage for curation.

Revision ID: 20260911_0006
Revises: 20260910_0005
Create Date: 2026-09-11
"""

import sqlalchemy as sa

from alembic import op

revision = "20260911_0006"
down_revision = "20260910_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_configurations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("provider_label", sa.String(length=128), nullable=False),
        sa.Column("api_protocol", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )


def downgrade() -> None:
    op.drop_table("llm_configurations")
