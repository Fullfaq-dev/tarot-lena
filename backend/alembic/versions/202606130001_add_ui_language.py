"""add ui_language to user_settings

Revision ID: 202606130001
Revises: 202606090005
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa

revision = "202606130001"
down_revision = "202606090005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("ui_language", sa.String(length=8), server_default="ru", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "ui_language")
