"""add product_entitlements, drop product_usages unique constraint

Revision ID: 202607060002
Revises: 202607060001
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607060002"
down_revision: str | None = "202607060001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_entitlements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uses_remaining", sa.Integer(), nullable=True),
        sa.Column("source_payment_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["source_payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_entitlements_user_id", "product_entitlements", ["user_id"])
    op.create_index("ix_product_entitlements_kind", "product_entitlements", ["kind"])
    op.drop_constraint("uq_user_product_level", "product_usages", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_user_product_level", "product_usages", ["user_id", "product_id", "level"]
    )
    op.drop_index("ix_product_entitlements_kind", table_name="product_entitlements")
    op.drop_index("ix_product_entitlements_user_id", table_name="product_entitlements")
    op.drop_table("product_entitlements")
