"""add product_usages table

Revision ID: 202607060001
Revises: 202606270001
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607060001"
down_revision: str | None = "202606270001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_usages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=32), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("payment_id", sa.String(length=36), nullable=True),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", "level", name="uq_user_product_level"),
    )
    op.create_index("ix_product_usages_user_id", "product_usages", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_product_usages_user_id", table_name="product_usages")
    op.drop_table("product_usages")
