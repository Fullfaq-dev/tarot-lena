"""web quiz tables

Revision ID: 202609200001
Revises: 202607130001
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202609200001"
down_revision: str | None = "202607130001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "web_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("guest_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("utm", sa.JSON(), nullable=False),
        sa.Column("metrika_client_id", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("telegram", sa.String(length=255), nullable=True),
        sa.Column("marketing_opt_in", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("privacy_opt_in", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("unlimited_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_web_sessions_guest_id", "web_sessions", ["guest_id"], unique=True)
    op.create_index("ix_web_sessions_user_id", "web_sessions", ["user_id"])

    op.create_table(
        "web_readings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(), sa.ForeignKey("web_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("card_id", sa.String(length=64), nullable=False),
        sa.Column("branch", sa.String(length=16), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="mini"),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("mini", sa.JSON(), nullable=False),
        sa.Column("paid_text", sa.Text(), nullable=True),
        sa.Column("payment_id", sa.String(), sa.ForeignKey("payments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_web_readings_token", "web_readings", ["token"], unique=True)
    op.create_index("ix_web_readings_session_id", "web_readings", ["session_id"])
    op.create_index("ix_web_readings_card_id", "web_readings", ["card_id"])
    op.create_index("ix_web_readings_status", "web_readings", ["status"])

    op.create_table(
        "web_card_overrides",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("card_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_web_card_overrides_card_id", "web_card_overrides", ["card_id"], unique=True)

    op.create_table(
        "web_matrix_cache",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("cache_key", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_web_matrix_cache_key", "web_matrix_cache", ["cache_key"], unique=True)


def downgrade() -> None:
    op.drop_table("web_matrix_cache")
    op.drop_table("web_card_overrides")
    op.drop_table("web_readings")
    op.drop_table("web_sessions")
