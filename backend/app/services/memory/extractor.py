import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Memory, MemoryType, RelationshipPerson, User

# Имя: кириллица, с заглавной, от 2 букв.
_NAME = r"([А-ЯЁ][а-яё]{1,})"

PERSON_PATTERNS = [
    rf"(?:зовут|зовёт|зовутся)\s+{_NAME}",
    rf"(?:моя|мою|мой|моей|моего)\s+(?:жена|жену|муж|мужа|супруг|супругу|супруга|дочь|сын|дочери|сына)\s+{_NAME}",
    rf"(?:жена|жену|муж|мужа|супруг|супругу|супруга|дочь|сын)\s+(?:—|-|:)?\s*{_NAME}",
    rf"\b(?:с|о|об|про)\s+{_NAME}",
]

# Слова, которые не являются именами людей.
_NAME_STOPWORDS = {
    "запомни",
    "запиши",
    "запомню",
    "важно",
    "привет",
    "спасибо",
    "пожалуйста",
    "таро",
    "расклад",
    "карта",
    "линия",
    "жизни",
    "душевная",
    "гармония",
    "история",
    "момент",
    "путь",
    "энергия",
    "здоровье",
    "чем",
    "том",
    "этом",
    "тебе",
    "меня",
    "того",
    "этого",
    "нас",
    "вас",
    "ней",
    "нем",
    "зовут",
    "зовутся",
    "твоём",
    "твоем",
    "твою",
    "твоей",
    "прошлый",
    "прошлом",
    "раз",
    "максим",
}

IMPORTANT_MARKERS = {
    MemoryType.RELATIONSHIP.value: [
        "расстался",
        "рассталась",
        "жена",
        "жену",
        "жены",
        "муж",
        "мужа",
        "мужу",
        "супруг",
        "супруга",
        "супругу",
        "бывшая",
        "бывший",
        "конфликт",
        "запомни",
        "запиши",
        "не забудь",
    ],
    MemoryType.WORK.value: ["работа", "бизнес", "клиент", "проект", "повышение", "уволился"],
    MemoryType.MONEY.value: ["деньги", "долг", "кредит", "доход", "прибыль"],
    MemoryType.GOAL.value: ["цель", "хочу", "планирую", "мечтаю"],
}

_REMEMBER_REQUEST = re.compile(r"\b(?:запомни|запиши|не забудь)\b", re.IGNORECASE)
_ASSISTANT_NAME = re.compile(r"\*\*([А-ЯЁ][а-яё]{1,})\*\*")


class MemoryExtractor:
    async def extract_from_dialog(
        self,
        session: AsyncSession,
        user: User,
        user_text: str,
        assistant_text: str,
    ) -> None:
        memory_type = self._detect_memory_type(user_text)
        if memory_type:
            session.add(
                Memory(
                    user_id=user.id,
                    type=memory_type,
                    importance=5 if _REMEMBER_REQUEST.search(user_text) else 4,
                    description=user_text[:1000],
                )
            )

        names = self._extract_people(user_text)
        if _REMEMBER_REQUEST.search(user_text):
            names.update(self._extract_people_from_assistant(assistant_text))

        now = datetime.now(timezone.utc)
        for name in names:
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
                    importance=5 if _REMEMBER_REQUEST.search(user_text) else 3,
                    notes=f"Пользователь упомянул: {user_text[:500]}",
                    last_mentioned_at=now,
                )
                session.add(person)
            else:
                person.notes = f"{person.notes or ''}\nНовое упоминание: {user_text[:500]}".strip()
                person.last_mentioned_at = now
                if _REMEMBER_REQUEST.search(user_text):
                    person.importance = max(person.importance, 5)
                    person.relationship_type = self._guess_relationship_type(user_text)

    def _detect_memory_type(self, text: str) -> str | None:
        lower = text.lower()
        for memory_type, markers in IMPORTANT_MARKERS.items():
            if any(marker in lower for marker in markers):
                return memory_type
        return None

    def _extract_people(self, text: str) -> set[str]:
        names: set[str] = set()
        for pattern in PERSON_PATTERNS:
            for match in re.finditer(pattern, text):
                name = (match.group(1) if match.lastindex else match.group(0)).strip()
                if self._is_valid_name(name):
                    names.add(self._normalize_name(name))
        return names

    def _extract_people_from_assistant(self, text: str) -> set[str]:
        names: set[str] = set()
        for match in _ASSISTANT_NAME.finditer(text):
            name = match.group(1).strip()
            if self._is_valid_name(name):
                names.add(self._normalize_name(name))
        for match in re.finditer(rf"(?:зовут|зовёт)\s+{_NAME}", text):
            name = match.group(1).strip()
            if self._is_valid_name(name):
                names.add(self._normalize_name(name))
        return names

    def _normalize_name(self, name: str) -> str:
        cleaned = name.strip()
        if not cleaned:
            return cleaned
        return cleaned[0].upper() + cleaned[1:]

    def _is_valid_name(self, name: str) -> bool:
        cleaned = name.strip()
        if len(cleaned) < 2:
            return False
        if cleaned.casefold() in _NAME_STOPWORDS:
            return False
        # После предлога «о/про» часто попадают служебные слова вроде «чем».
        if len(cleaned) <= 4 and cleaned[0].islower():
            return False
        return True

    def _guess_relationship_type(self, text: str) -> str:
        lower = text.lower()
        if "бывш" in lower:
            return "бывшие отношения"
        if any(word in lower for word in ("жена", "жену", "жены", "муж", "мужа", "супруг", "супруга", "супругу")):
            return "семья"
        if "партнер" in lower or "бизнес" in lower:
            return "работа/бизнес"
        if "друг" in lower or "подруга" in lower:
            return "дружба"
        if "ребен" in lower or "сын" in lower or "дочь" in lower:
            return "ребенок"
        return "важный человек"
