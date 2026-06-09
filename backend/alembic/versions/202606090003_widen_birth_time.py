"""widen birth_time column

Revision ID: 202606090003
Revises: 202606090002
Create Date: 2026-06-09 09:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606090003"
down_revision: str | None = "202606090002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "soul_profiles",
        "birth_time",
        existing_type=sa.String(length=16),
        type_=sa.String(length=128),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "soul_profiles",
        "birth_time",
        existing_type=sa.String(length=128),
        type_=sa.String(length=16),
        existing_nullable=True,
    )
