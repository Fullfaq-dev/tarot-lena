"""add user referral_reward_percent

Revision ID: 202606270001
Revises: 202606260001
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa

revision = "202606270001"
down_revision = "202606260001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "referral_reward_percent",
            sa.Integer(),
            nullable=False,
            server_default="40",
        ),
    )
    op.execute(
        "UPDATE users SET referral_reward_percent = 50 WHERE telegram_id = 8082467889"
    )
    op.execute(
        """
        UPDATE referrals
        SET reward_percent = 50
        WHERE referrer_user_id IN (
            SELECT id FROM users WHERE telegram_id = 8082467889
        )
        """
    )


def downgrade() -> None:
    op.drop_column("users", "referral_reward_percent")
