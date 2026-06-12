from sqlalchemy import func, select

from app.database.models import Memory, MemoryType, User
from app.database.session import AsyncSessionLocal
from app.services.billing.limits import MEMORY_PAGE_SIZE

MEMORY_TYPE_LABELS = {
    MemoryType.EVENT.value: "Событие",
    MemoryType.GOAL.value: "Цель",
    MemoryType.PREFERENCE.value: "Предпочтение",
    MemoryType.RELATIONSHIP.value: "Отношения",
    MemoryType.WORK.value: "Работа",
    MemoryType.HEALTH.value: "Здоровье",
    MemoryType.MONEY.value: "Деньги",
    MemoryType.OTHER.value: "Другое",
}


def format_importance(value: int) -> str:
    clamped = max(1, min(5, value))
    return "★" * clamped + "☆" * (5 - clamped)


class MemoryPanelService:
    async def list_page(
        self, telegram_id: int, page: int = 0
    ) -> tuple[str, list[Memory], int, int]:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы создать твой профиль.", [], 0, 0

            total = await session.scalar(
                select(func.count())
                .select_from(Memory)
                .where(Memory.user_id == user.id, Memory.is_active.is_(True))
            )
            total = int(total or 0)
            if total == 0:
                return (
                    "🧠 Память обо мне\n\n"
                    "Пока записей нет — бот запоминает важное из переписки автоматически. "
                    "Можешь добавить факты вручную кнопкой ниже.",
                    [],
                    0,
                    0,
                )

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

            lines = [
                "🧠 Память обо мне",
                "Сортировка: сначала более важные записи.",
                f"Страница {page + 1} из {total_pages}\n",
                "Нажми на запись, чтобы открыть полностью:\n",
            ]
            for index, memory in enumerate(items, start=offset + 1):
                preview = memory.description.strip().replace("\n", " ")
                if len(preview) > 72:
                    preview = preview[:72] + "…"
                type_label = MEMORY_TYPE_LABELS.get(memory.type, memory.type)
                lines.append(
                    f"{index}. {format_importance(memory.importance)} · {type_label}\n   {preview}"
                )
            return "\n".join(lines), items, page, total_pages

    async def detail_text(self, telegram_id: int, memory_id: str) -> str | None:
        async with AsyncSessionLocal() as session:
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

            type_label = MEMORY_TYPE_LABELS.get(memory.type, memory.type)
            when = memory.created_at.strftime("%d.%m.%Y %H:%M")
            happened = (
                f"\nДата события: {memory.happened_at.strftime('%d.%m.%Y')}"
                if memory.happened_at
                else ""
            )
            return (
                "🧠 Запись памяти\n\n"
                f"Важность: {format_importance(memory.importance)} ({memory.importance}/5)\n"
                f"Тип: {type_label}\n"
                f"Добавлено: {when}{happened}\n\n"
                f"{memory.description.strip()}"
            )

    async def add_manual(self, telegram_id: int, description: str) -> tuple[bool, str]:
        text = description.strip()
        if len(text) < 3:
            return False, "Слишком коротко — напиши хотя бы несколько слов."
        if len(text) > 1000:
            text = text[:1000]

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return False, "Сначала нажми /start, чтобы создать твой профиль."

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
            return True, "Запись добавлена в память."

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
