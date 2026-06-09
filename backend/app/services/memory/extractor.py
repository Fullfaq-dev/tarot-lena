import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Memory, MemoryType, RelationshipPerson, User

PERSON_PATTERNS = [
    r"\b(?:с|о|об|про)\s+([А-ЯЁ][а-яё]{2,})",
    r"\b(Анна|Аня|Мария|Маша|Ольга|Елена|Ирина|Дмитрий|Сергей|Алексей|Иван)\b",
]

IMPORTANT_MARKERS = {
    MemoryType.RELATIONSHIP.value: ["расстался", "рассталась", "жена", "муж", "бывшая", "бывший", "конфликт"],
    MemoryType.WORK.value: ["работа", "бизнес", "клиент", "проект", "повышение", "уволился"],
    MemoryType.MONEY.value: ["деньги", "долг", "кредит", "доход", "прибыль"],
    MemoryType.GOAL.value: ["цель", "хочу", "планирую", "мечтаю"],
}


class MemoryExtractor:
    async def extract_from_dialog(
        self,
        session: AsyncSession,
        user: User,
        user_text: str,
        assistant_text: str,
    ) -> None:
        del assistant_text
        memory_type = self._detect_memory_type(user_text)
        if memory_type:
            session.add(
                Memory(
                    user_id=user.id,
                    type=memory_type,
                    importance=4,
                    description=user_text[:1000],
                )
            )

        for name in self._extract_people(user_text):
            normalized = name.casefold()
            person = await session.scalar(
                select(RelationshipPerson).where(
                    RelationshipPerson.user_id == user.id,
                    RelationshipPerson.normalized_name == normalized,
                )
            )
            if person is None:
                person = RelationshipPerson(
                    user_id=user.id,
                    display_name=name,
                    normalized_name=normalized,
                    relationship_type=self._guess_relationship_type(user_text),
                    notes=f"Пользователь упомянул: {user_text[:500]}",
                )
                session.add(person)
            else:
                person.notes = f"{person.notes or ''}\nНовое упоминание: {user_text[:500]}".strip()

    def _detect_memory_type(self, text: str) -> str | None:
        lower = text.lower()
        for memory_type, markers in IMPORTANT_MARKERS.items():
            if any(marker in lower for marker in markers):
                return memory_type
        return None

    def _extract_people(self, text: str) -> set[str]:
        names: set[str] = set()
        for pattern in PERSON_PATTERNS:
            names.update(match.group(1) if match.groups() else match.group(0) for match in re.finditer(pattern, text))
        return {name.strip() for name in names if len(name.strip()) > 2}

    def _guess_relationship_type(self, text: str) -> str:
        lower = text.lower()
        if "бывш" in lower:
            return "бывшие отношения"
        if "жена" in lower or "муж" in lower:
            return "семья"
        if "партнер" in lower or "бизнес" in lower:
            return "работа/бизнес"
        if "друг" in lower or "подруга" in lower:
            return "дружба"
        if "ребен" in lower or "сын" in lower or "дочь" in lower:
            return "ребенок"
        return "важный человек"
