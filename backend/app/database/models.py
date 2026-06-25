from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin


class SubscriptionTier(StrEnum):
    FREE = "free"
    PLUS = "plus"
    PREMIUM = "premium"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MemoryType(StrEnum):
    EVENT = "event"
    GOAL = "goal"
    PREFERENCE = "preference"
    RELATIONSHIP = "relationship"
    WORK = "work"
    HEALTH = "health"
    MONEY = "money"
    OTHER = "other"


class MediaJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(16))
    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    balance_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    free_messages_used_month: Mapped[int] = mapped_column(Integer, default=0)
    free_readings_used_month: Mapped[int] = mapped_column(Integer, default=0)
    free_infographics_used_month: Mapped[int] = mapped_column(Integer, default=0)
    free_limits_month: Mapped[str | None] = mapped_column(String(7))
    usdt_trc20_wallet: Mapped[str | None] = mapped_column(String(64))
    gift_claimed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    settings: Mapped["UserSettings"] = relationship(back_populates="user", cascade="all, delete-orphan")
    soul_profile: Mapped["SoulProfile"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSettings(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    voice_preset: Mapped[str] = mapped_column(String(64), default="female_mystical")
    ui_language: Mapped[str] = mapped_column(String(8), default="ru")
    language_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    quiet_hours_start: Mapped[str] = mapped_column(String(5), default="22:00")
    quiet_hours_end: Mapped[str] = mapped_column(String(5), default="09:00")
    daily_card_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    proactive_messages_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="settings")


class OnboardingSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "onboarding_sessions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    current_step: Mapped[str] = mapped_column(String(64), default="name")
    answers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SoulProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "soul_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    birth_date: Mapped[date | None] = mapped_column(Date)
    birth_time: Mapped[str | None] = mapped_column(String(128))
    birth_city: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(64))
    relationship_status: Mapped[str | None] = mapped_column(String(128))
    has_children: Mapped[str | None] = mapped_column(String(128))
    profession: Mapped[str | None] = mapped_column(String(255))
    six_month_goal: Mapped[str | None] = mapped_column(Text)
    main_concern: Mapped[str | None] = mapped_column(String(128))
    belief_system: Mapped[str | None] = mapped_column(String(128))
    character_summary: Mapped[str | None] = mapped_column(Text)
    archetype: Mapped[str | None] = mapped_column(String(128))
    personal_arcana: Mapped[str | None] = mapped_column(String(128))
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="soul_profile")


class Subscription(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    tier: Mapped[str] = mapped_column(String(32), default=SubscriptionTier.FREE.value)
    status: Mapped[str] = mapped_column(String(32), default="active")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str | None] = mapped_column(String(64))
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="subscription")


class Message(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    cost_rub: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Memory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "memories"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(64), default=MemoryType.OTHER.value)
    importance: Mapped[int] = mapped_column(Integer, default=3)
    happened_at: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text)
    source_message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RelationshipPerson(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "relationship_people"
    __table_args__ = (UniqueConstraint("user_id", "normalized_name", name="uq_user_person_name"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(255))
    relationship_type: Mapped[str] = mapped_column(String(128), default="unknown")
    sentiment: Mapped[str | None] = mapped_column(String(64))
    importance: Mapped[int] = mapped_column(Integer, default=3)
    notes: Mapped[str | None] = mapped_column(Text)
    last_mentioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RelationshipEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "relationship_events"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("relationship_people.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(128), default="mention")
    description: Mapped[str] = mapped_column(Text)
    happened_at: Mapped[date | None] = mapped_column(Date)
    importance: Mapped[int] = mapped_column(Integer, default=3)


class RelationshipMention(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "relationship_mentions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("relationship_people.id", ondelete="CASCADE"))
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))


class TarotCard(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tarot_cards"

    slug: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    arcana: Mapped[str] = mapped_column(String(64))
    number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str] = mapped_column(String(512))


class TarotReading(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tarot_readings"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reading_type: Mapped[str] = mapped_column(String(128))
    question: Mapped[str] = mapped_column(Text)
    cards: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    interpretation: Mapped[str] = mapped_column(Text)


class DailyPrediction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "daily_predictions"
    __table_args__ = (UniqueConstraint("user_id", "prediction_date", name="uq_user_daily_prediction"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    prediction_date: Mapped[date] = mapped_column(Date)
    tarot_card_id: Mapped[str | None] = mapped_column(ForeignKey("tarot_cards.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text)


class MediaJob(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "media_jobs"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(64), default="kie")
    provider_task_id: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), default=MediaJobStatus.PENDING.value)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)


class VoiceMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "voice_messages"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    telegram_file_id: Mapped[str] = mapped_column(String(512))
    transcript: Mapped[str | None] = mapped_column(Text)
    response_audio_url: Mapped[str | None] = mapped_column(String(1024))
    media_job_id: Mapped[str | None] = mapped_column(ForeignKey("media_jobs.id", ondelete="SET NULL"))


class Payment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64), default="platega")
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), index=True)
    purpose: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), default="pending")
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class BalanceTransaction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "balance_transactions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    reason: Mapped[str] = mapped_column(String(128))
    payment_id: Mapped[str | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
    usage_record_id: Mapped[str | None] = mapped_column(String(64))


class UsageRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "usage_records"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    feature: Mapped[str] = mapped_column(String(128))
    provider: Mapped[str] = mapped_column(String(64), default="kie")
    model: Mapped[str | None] = mapped_column(String(128))
    input_units: Mapped[int] = mapped_column(Integer, default=0)
    output_units: Mapped[int] = mapped_column(Integer, default=0)
    provider_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"))
    charged_rub: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Notification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notification_logs"

    notification_id: Mapped[str | None] = mapped_column(
        ForeignKey("notifications.id", ondelete="SET NULL")
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(64))
    message: Mapped[str | None] = mapped_column(Text)


class Referral(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "referrals"
    __table_args__ = (UniqueConstraint("referred_user_id", name="uq_referred_user"),)

    referrer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    referred_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    reward_percent: Mapped[int] = mapped_column(Integer, default=40)
    accrued_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))


class ReferralWithdrawalRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "referral_withdrawal_requests"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(64), default="pending")
    payout_details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    admin_comment: Mapped[str | None] = mapped_column(Text)


class GeneratedReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "generated_reports"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    report_type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(64), default="pending")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AnalyticsEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analytics_events"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    event_name: Mapped[str] = mapped_column(String(128), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AdminUser(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(64), default="owner")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AdminAuditLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "admin_audit_logs"

    admin_user_id: Mapped[str | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str | None] = mapped_column(String(128))
    entity_id: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
