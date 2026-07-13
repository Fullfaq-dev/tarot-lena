"""add leia broadcast settings

Revision ID: 202607130001
Revises: 202607060002
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607130001"
down_revision: str | None = "202607060002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("morning_digest_enabled", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "user_settings",
        sa.Column("weekly_horoscope_enabled", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "user_settings",
        sa.Column("free_morning_week_ends_at", sa.Date(), nullable=True),
    )
    op.add_column(
        "user_settings",
        sa.Column("mini_portrait_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE user_settings
        SET morning_digest_enabled = daily_card_enabled,
            weekly_horoscope_enabled = true
        """
    )


def downgrade() -> None:
    op.drop_column("user_settings", "mini_portrait_sent_at")
    op.drop_column("user_settings", "free_morning_week_ends_at")
    op.drop_column("user_settings", "weekly_horoscope_enabled")
    op.drop_column("user_settings", "morning_digest_enabled")
