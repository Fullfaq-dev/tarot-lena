"""add free_limits_month to users

Revision ID: 202606130003
Revises: 202606130002
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa

revision = "202606130003"
down_revision = "202606130002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("free_limits_month", sa.String(length=7), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "free_limits_month")
