"""add free_infographics_used_month to users

Revision ID: 202606240001
Revises: 202606130003
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa

revision = "202606240001"
down_revision = "202606130003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "free_infographics_used_month",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "free_infographics_used_month")
