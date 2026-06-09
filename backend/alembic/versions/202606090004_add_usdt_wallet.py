"""add usdt trc20 wallet to users

Revision ID: 202606090004
Revises: 202606090003
Create Date: 2026-06-09 21:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606090004"
down_revision: str | None = "202606090003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("usdt_trc20_wallet", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "usdt_trc20_wallet")
