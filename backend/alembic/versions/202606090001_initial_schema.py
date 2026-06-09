"""initial schema

Revision ID: 202606090001
Revises:
Create Date: 2026-06-09 09:05:00
"""

from collections.abc import Sequence

from alembic import op

from app.database import Base, models  # noqa: F401

revision: str = "202606090001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
