"""add landing analytics tables

Revision ID: 202606260001
Revises: 202606250001
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa

revision = "202606260001"
down_revision = "202606250001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "landing_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("visitor_id", sa.String(length=64), nullable=False),
        sa.Column("page", sa.String(length=64), nullable=False, server_default="index"),
        sa.Column("referrer", sa.String(length=2048), nullable=True),
        sa.Column("utm_source", sa.String(length=128), nullable=True),
        sa.Column("utm_medium", sa.String(length=128), nullable=True),
        sa.Column("utm_campaign", sa.String(length=128), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("device_type", sa.String(length=32), nullable=True),
        sa.Column("screen_width", sa.Integer(), nullable=True),
        sa.Column("screen_height", sa.Integer(), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("max_scroll_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_landing_sessions_visitor_id", "landing_sessions", ["visitor_id"])
    op.create_index("ix_landing_sessions_page", "landing_sessions", ["page"])
    op.create_index("ix_landing_sessions_created_at", "landing_sessions", ["created_at"])

    op.create_table(
        "landing_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("element_id", sa.String(length=128), nullable=True),
        sa.Column("element_label", sa.String(length=255), nullable=True),
        sa.Column("section_id", sa.String(length=64), nullable=True),
        sa.Column("value", sa.String(length=128), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["session_id"], ["landing_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_landing_events_session_id", "landing_events", ["session_id"])
    op.create_index("ix_landing_events_event_type", "landing_events", ["event_type"])
    op.create_index("ix_landing_events_section_id", "landing_events", ["section_id"])
    op.create_index("ix_landing_events_created_at", "landing_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_landing_events_created_at", table_name="landing_events")
    op.drop_index("ix_landing_events_section_id", table_name="landing_events")
    op.drop_index("ix_landing_events_event_type", table_name="landing_events")
    op.drop_index("ix_landing_events_session_id", table_name="landing_events")
    op.drop_table("landing_events")
    op.drop_index("ix_landing_sessions_created_at", table_name="landing_sessions")
    op.drop_index("ix_landing_sessions_page", table_name="landing_sessions")
    op.drop_index("ix_landing_sessions_visitor_id", table_name="landing_sessions")
    op.drop_table("landing_sessions")
