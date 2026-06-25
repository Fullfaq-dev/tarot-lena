"""add gift_claimed to users

Revision ID: 202606250001
Revises: 202606240001
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa

revision = "202606250001"
down_revision = "202606240001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "gift_claimed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "gift_claimed")
