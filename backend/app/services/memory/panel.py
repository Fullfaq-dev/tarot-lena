from sqlalchemy import func, select

from app.bot.i18n import normalize_language, t
from app.bot.i18n_services import MEMORY_TYPE_I18N
from app.database.models import Memory, MemoryType, User, UserSettings
from app.database.session import AsyncSessionLocal
from app.services.billing.limits import MEMORY_PAGE_SIZE


def format_importance(value: int) -> str:
    clamped = max(1, min(5, value))
    return "★" * clamped + "☆" * (5 - clamped)


class MemoryPanelService:
    async def _lang(self, session, telegram_id: int) -> str:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            return "en"
        settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
        return normalize_language(settings.ui_language if settings else "en")

    def _type_label(self, memory_type: str, lang: str) -> str:
        key = MEMORY_TYPE_I18N.get(memory_type)
        return t(key, lang) if key else memory_type

    async def list_page(
        self, telegram_id: int, page: int = 0
    ) -> tuple[str, list[Memory], int, int]:
        async with AsyncSessionLocal() as session:
            lang = await self._lang(session, telegram_id)
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", lang), [], 0, 0

            total = await session.scalar(
                select(func.count())
                .select_from(Memory)
                .where(Memory.user_id == user.id, Memory.is_active.is_(True))
            )
            total = int(total or 0)
            if total == 0:
                return t("memory_empty", lang), [], 0, 0

            total_pages = max(1, (total + MEMORY_PAGE_SIZE - 1) // MEMORY_PAGE_SIZE)
            page = max(0, min(page, total_pages - 1))
            offset = page * MEMORY_PAGE_SIZE

            memories = await session.scalars(
                select(Memory)
                .where(Memory.user_id == user.id, Memory.is_active.is_(True))
                .order_by(Memory.importance.desc(), Memory.created_at.desc())
                .offset(offset)
                .limit(MEMORY_PAGE_SIZE)
            )
            items = list(memories)

            header = t(
                "memory_list_header",
                lang,
                page=t("history_page", lang, page=page + 1, total=total_pages),
            )
            lines = [header.rstrip("\n")]
            for index, memory in enumerate(items, start=offset + 1):
                preview = memory.description.strip().replace("\n", " ")
                if len(preview) > 72:
                    preview = preview[:72] + "…"
                type_label = self._type_label(memory.type, lang)
                lines.append(
                    f"{index}. {format_importance(memory.importance)} · {type_label}\n   {preview}"
                )
            return "\n".join(lines), items, page, total_pages

    async def detail_text(self, telegram_id: int, memory_id: str) -> str | None:
        async with AsyncSessionLocal() as session:
            lang = await self._lang(session, telegram_id)
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return None
            memory = await session.scalar(
                select(Memory).where(
                    Memory.id == memory_id,
                    Memory.user_id == user.id,
                    Memory.is_active.is_(True),
                )
            )
            if memory is None:
                return None

            type_label = self._type_label(memory.type, lang)
            when = memory.created_at.strftime("%d.%m.%Y %H:%M")
            happened = (
                t("memory_happened_at", lang, date=memory.happened_at.strftime("%d.%m.%Y"))
                if memory.happened_at
                else ""
            )
            return t(
                "memory_detail",
                lang,
                stars=format_importance(memory.importance),
                importance=memory.importance,
                type=type_label,
                when=when,
                happened=happened,
                description=memory.description.strip(),
            )

    async def add_manual(self, telegram_id: int, description: str) -> tuple[bool, str]:
        text = description.strip()
        async with AsyncSessionLocal() as session:
            lang = await self._lang(session, telegram_id)
        if len(text) < 3:
            return False, t("memory_too_short", lang)
        if len(text) > 1000:
            text = text[:1000]

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return False, t("error_need_start", lang)

            session.add(
                Memory(
                    user_id=user.id,
                    type=MemoryType.PREFERENCE.value,
                    importance=4,
                    description=text,
                    is_active=True,
                )
            )
            await session.commit()
            return True, t("memory_added", lang)

    async def deactivate(self, telegram_id: int, memory_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return False
            memory = await session.scalar(
                select(Memory).where(Memory.id == memory_id, Memory.user_id == user.id)
            )
            if memory is None or not memory.is_active:
                return False
            memory.is_active = False
            await session.commit()
            return True
