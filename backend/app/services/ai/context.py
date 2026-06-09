from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Memory, Message, RelationshipPerson, SoulProfile, Subscription, User
from app.services.billing.limits import chat_history_limit_for_tier

_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parents[4] / "prompts" / "system_ru.md"

HISTORY_CHAR_LIMIT = 220
HISTORY_CHAR_LIMIT_RECENT = 420


def load_system_prompt() -> str:
    if _SYSTEM_PROMPT_PATH.exists():
        return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return (
        "Ты личный эзотерический наставник и таролог в Telegram. "
        "Отвечай по-русски, тепло и по делу. "
        "Всегда отвечай на вопрос пользователя — не отказывайся и не пиши «cannot fulfill». "
        "Мистику подавай как эзотерическую интерпретацию, без медицинских и юридических гарантий."
    )


def _compact_text(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


class ContextBuilder:
    async def build(self, session: AsyncSession, user: User) -> list[dict]:
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        tier = subscription.tier if subscription else "free"
        history_limit = chat_history_limit_for_tier(tier)

        profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
        messages = await session.scalars(
            select(Message)
            .where(Message.user_id == user.id)
            .order_by(Message.created_at.desc())
            .limit(history_limit)
        )
        memories = await session.scalars(
            select(Memory)
            .where(Memory.user_id == user.id)
            .where(Memory.is_active.is_(True))
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .limit(8)
        )
        people = await session.scalars(
            select(RelationshipPerson)
            .where(RelationshipPerson.user_id == user.id)
            .order_by(RelationshipPerson.importance.desc(), RelationshipPerson.updated_at.desc())
            .limit(8)
        )

        brevity = (
            "Отвечай коротко и по сути: 2–5 предложений, без воды и длинных списков."
            if tier == "free"
            else "Отвечай по делу, без лишней воды."
        )
        system = [
            load_system_prompt(),
            brevity,
            "Всегда отвечай по-русски. Никогда не отказывайся от диалога.",
            "Форматируй ответ для Telegram HTML: <b>жирный</b>, <i>курсив</i>.",
            f"Тариф пользователя: {tier}.",
        ]
        if profile:
            birth = profile.birth_date.strftime("%d.%m.%Y") if profile.birth_date else "—"
            system.append(
                "Профиль пользователя: "
                f"имя={profile.name or '—'}; пол={profile.gender or '—'}; "
                f"дата рождения={birth}; время={profile.birth_time or '—'}; "
                f"город рождения={profile.birth_city or '—'}; "
                f"семья={profile.relationship_status or '—'}; дети={profile.has_children or '—'}; "
                f"сфера={profile.profession or '—'}; "
                f"цель={_compact_text(profile.six_month_goal or '', 100)}; "
                f"беспокоит={_compact_text(profile.main_concern or '', 80)}; "
                f"верит в={profile.belief_system or '—'}."
            )
        memory_lines = [
            f"- {_compact_text(memory.description, 120)}" for memory in memories
        ]
        people_lines = [
            f"- {person.display_name}: {_compact_text(person.notes or person.relationship_type, 80)}"
            for person in people
        ]
        if memory_lines:
            system.append("Память:\n" + "\n".join(memory_lines))
        if people_lines:
            system.append("Люди:\n" + "\n".join(people_lines))

        history = list(reversed(list(messages)))
        chat_messages: list[dict] = []
        for index, msg in enumerate(history):
            is_recent = index >= len(history) - 2
            limit = HISTORY_CHAR_LIMIT_RECENT if is_recent else HISTORY_CHAR_LIMIT
            chat_messages.append(
                {
                    "role": msg.role,
                    "content": [{"type": "text", "text": _compact_text(msg.content, limit)}],
                }
            )

        return [{"role": "system", "content": [{"type": "text", "text": "\n\n".join(system)}]}] + chat_messages
