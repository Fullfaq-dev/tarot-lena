"""add language_locked to user_settings

Revision ID: 202606130002
Revises: 202606130001
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa

revision = "202606130002"
down_revision = "202606130001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("language_locked", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "language_locked")
