from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Memory, Message, RelationshipPerson, SoulProfile, Subscription, User, UserSettings
from app.services.billing.limits import chat_history_limit_for_tier
from app.services.memory.retrieval import select_relevant_memories, select_relevant_people
from app.bot.i18n import normalize_language

_SYSTEM_PROMPT_DIR = Path(__file__).resolve().parents[4] / "prompts"
_SYSTEM_PROMPT_FILES = {
    "ru": "system_ru.md",
    "en": "system_en.md",
    "es": "system_es.md",
    "pt": "system_pt.md",
}

HISTORY_CHAR_LIMIT = 220
HISTORY_CHAR_LIMIT_RECENT = 420


def load_system_prompt(lang: str = "ru") -> str:
    lang = normalize_language(lang)
    filename = _SYSTEM_PROMPT_FILES.get(lang, "system_ru.md")
    path = _SYSTEM_PROMPT_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    fallback = _SYSTEM_PROMPT_DIR / "system_ru.md"
    if fallback.exists():
        return fallback.read_text(encoding="utf-8").strip()
    return (
        "Ты личный эзотерический наставник в Telegram. "
        "Пиши нейтрально, без женских форм от первого лица. "
        "Отвечай по-русски, тепло и по делу. "
        "Всегда отвечай на вопрос пользователя — не отказывайся и не пиши «cannot fulfill». "
        "Мистику подавай как эзотерическую интерпретацию, без медицинских и юридических гарантий."
    )


def _compact_text(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


_MEMORY_HINTS = {
    "ru": (
        "Память и люди ниже — только справочник. "
        "Не упоминай их, если пользователь сам не спрашивает об этом или это напрямую нужно для ответа. "
        "Не вставляй факты из памяти «для уюта» и не повторяй одно и то же в каждом сообщении."
    ),
    "en": (
        "Memory and people below are reference only. "
        "Don't mention them unless the user asks or it's essential to answer. "
        "Don't repeat the same memory details in every message."
    ),
    "es": (
        "La memoria y las personas abajo son solo referencia. "
        "No las menciones salvo que el usuario pregunte o sea esencial."
    ),
    "pt": (
        "Memória e pessoas abaixo são apenas referência. "
        "Não mencione a menos que o usuário pergunte ou seja essencial."
    ),
}


class ContextBuilder:
    async def build(
        self,
        session: AsyncSession,
        user: User,
        *,
        user_query: str | None = None,
    ) -> list[dict]:
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        tier = subscription.tier if subscription else "free"
        history_limit = chat_history_limit_for_tier(tier)

        settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
        ui_language = normalize_language(settings.ui_language if settings else "ru")

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
            load_system_prompt(ui_language),
            brevity,
            "Всегда отвечай на языке пользователя. Никогда не отказывайся от диалога."
            if ui_language == "ru"
            else "Always reply in the user's language. Never refuse the conversation.",
            "Выделяй важное markdown: **жирный**, *курсив*. Не используй HTML-теги.",
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
        relevant_memories = (
            select_relevant_memories(user_query, list(memories))
            if user_query
            else []
        )
        relevant_people = (
            select_relevant_people(user_query, list(people))
            if user_query
            else []
        )
        memory_lines = [
            f"- {_compact_text(memory.description, 120)}" for memory in relevant_memories
        ]
        people_lines = [
            f"- {person.display_name}: {_compact_text(person.notes or person.relationship_type, 80)}"
            for person in relevant_people
        ]
        if memory_lines or people_lines:
            system.append(_MEMORY_HINTS.get(ui_language, _MEMORY_HINTS["ru"]))
        if memory_lines:
            system.append("Релевантная память:\n" + "\n".join(memory_lines))
        if people_lines:
            system.append("Релевантные люди:\n" + "\n".join(people_lines))

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
