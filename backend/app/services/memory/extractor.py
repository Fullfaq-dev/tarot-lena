import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Memory, MemoryType, RelationshipPerson, User
from app.services.ai.kie_client import KieClient

_NAME = r"([А-ЯЁ][а-яё]{1,})"

PERSON_PATTERNS = [
    rf"(?:зовут|зовёт|зовутся)\s+{_NAME}",
    rf"(?:моя|мою|мой|моей|моего)\s+(?:жена|жену|муж|мужа|супруг|супругу|супруга|дочь|сын|дочери|сына)\s+{_NAME}",
    rf"(?:жена|жену|муж|мужа|супруг|супругу|супруга|дочь|сын)\s+(?:—|-|:)?\s*{_NAME}",
    rf"\b(?:с|о|об|про)\s+{_NAME}",
]

_NAME_STOPWORDS = {
    "запомни", "запиши", "запомню", "важно", "привет", "спасибо", "пожалуйста",
    "таро", "расклад", "карта", "линия", "жизни", "чем", "том", "этом", "тебе",
    "меня", "зовут", "зовутся", "твоём", "твоем", "твою", "твоей", "прошлый", "раз",
}

IMPORTANT_MARKERS = {
    MemoryType.RELATIONSHIP.value: [
        "расстался", "рассталась", "жена", "жену", "жены", "муж", "мужа", "мужу",
        "супруг", "супруга", "супругу", "бывшая", "бывший", "конфликт", "запомни", "запиши",
    ],
    MemoryType.WORK.value: ["работа", "бизнес", "клиент", "проект", "повышение", "уволился"],
    MemoryType.MONEY.value: ["деньги", "долг", "кредит", "доход", "прибыль"],
    MemoryType.GOAL.value: ["цель", "хочу", "планирую", "мечтаю"],
}

_VALID_MEMORY_TYPES = {t.value for t in MemoryType}
_VALID_RELATIONSHIP_TYPES = {
    "семья", "дружба", "ребенок", "работа/бизнес", "бывшие отношения", "важный человек", "unknown",
}

_GREETING_ONLY = re.compile(
    r"^(?:привет|здравствуй(?:те)?|hi|hello|ку|йо|хай|добрый\s+(?:день|вечер|утро))[\s!.?]*$",
    re.IGNORECASE,
)

_EXTRACTION_SYSTEM = (
    "Ты анализируешь диалог пользователя с эзотерическим ботом в Telegram.\n"
    "Извлеки только НОВЫЕ важные факты из сообщения пользователя.\n"
    "Если пользователь просит «запомни» — учти и подтверждение в ответе бота.\n"
    "Не выдумывай. Если важного нет — верни пустые списки.\n"
    "Верни ТОЛЬКО валидный JSON без markdown:\n"
    '{"memories":[{"type":"relationship|work|money|goal|health|preference|event|other",'
    '"importance":1,"description":"..."}],'
    '"people":[{"display_name":"Имя","relationship_type":"семья|дружба|ребенок|работа/бизнес|бывшие отношения|важный человек",'
    '"notes":"контекст","importance":3}]}'
)


@dataclass
class ExtractedMemory:
    type: str
    importance: int
    description: str


@dataclass
class ExtractedPerson:
    display_name: str
    relationship_type: str
    notes: str
    importance: int = 3


@dataclass
class ExtractionPayload:
    memories: list[ExtractedMemory] = field(default_factory=list)
    people: list[ExtractedPerson] = field(default_factory=list)


class MemoryExtractor:
    def __init__(self) -> None:
        self._kie = KieClient()

    async def extract_from_dialog(
        self,
        session: AsyncSession,
        user: User,
        user_text: str,
        assistant_text: str,
    ) -> dict[str, int] | None:
        """
        Извлекает память и людей из диалога.
        Возвращает usage API, если отработал ИИ-экстрактор (для биллинга).
        """
        usage: dict[str, int] | None = None
        payload: ExtractionPayload | None = None

        if self._should_use_ai(user_text):
            payload, usage = await self._extract_with_ai(user_text, assistant_text)

        if payload is None:
            payload = self._extract_with_regex(user_text, assistant_text)

        if payload.memories or payload.people:
            await self._persist(session, user, user_text, payload)

        return usage

    def _should_use_ai(self, user_text: str) -> bool:
        text = user_text.strip()
        if len(text) < 8:
            return False
        if _GREETING_ONLY.match(text):
            return False
        return True

    async def _extract_with_ai(
        self,
        user_text: str,
        assistant_text: str,
    ) -> tuple[ExtractionPayload | None, dict[str, int] | None]:
        messages = [
            {"role": "system", "content": [{"type": "text", "text": _EXTRACTION_SYSTEM}]},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Сообщение пользователя:\n{user_text}\n\n"
                            f"Ответ бота:\n{assistant_text[:1500]}"
                        ),
                    }
                ],
            },
        ]
        try:
            raw = await self._kie.chat_completion(messages, reasoning_effort="low")
            usage = dict(self._kie.last_usage) if self._kie.last_usage else None
            payload = self._parse_ai_response(raw)
            if not payload.memories and not payload.people:
                return None, usage
            return payload, usage
        except Exception:
            return None, None

    def _parse_ai_response(self, raw: str) -> ExtractionPayload:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return ExtractionPayload()
            parsed = json.loads(match.group(0))

        if not isinstance(parsed, dict):
            return ExtractionPayload()

        memories: list[ExtractedMemory] = []
        for item in parsed.get("memories") or []:
            if not isinstance(item, dict):
                continue
            description = str(item.get("description", "")).strip()
            if not description:
                continue
            memory_type = str(item.get("type", MemoryType.OTHER.value)).strip().lower()
            if memory_type not in _VALID_MEMORY_TYPES:
                memory_type = MemoryType.OTHER.value
            importance = max(1, min(5, int(item.get("importance", 4))))
            memories.append(ExtractedMemory(type=memory_type, importance=importance, description=description[:1000]))

        people: list[ExtractedPerson] = []
        for item in parsed.get("people") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("display_name", "")).strip()
            if not self._is_valid_name(name):
                continue
            relationship_type = str(item.get("relationship_type", "важный человек")).strip()
            if relationship_type not in _VALID_RELATIONSHIP_TYPES:
                relationship_type = "важный человек"
            notes = str(item.get("notes", "")).strip() or "Упомянут в диалоге"
            importance = max(1, min(5, int(item.get("importance", 3))))
            people.append(
                ExtractedPerson(
                    display_name=self._normalize_name(name),
                    relationship_type=relationship_type,
                    notes=notes[:500],
                    importance=importance,
                )
            )

        return ExtractionPayload(memories=memories, people=people)

    def _extract_with_regex(self, user_text: str, assistant_text: str) -> ExtractionPayload:
        memories: list[ExtractedMemory] = []
        memory_type = self._detect_memory_type(user_text)
        if memory_type:
            memories.append(
                ExtractedMemory(
                    type=memory_type,
                    importance=5 if re.search(r"\b(?:запомни|запиши)\b", user_text, re.I) else 4,
                    description=user_text[:1000],
                )
            )

        names = self._extract_people(user_text)
        if re.search(r"\b(?:запомни|запиши)\b", user_text, re.I):
            names.update(self._extract_people_from_assistant(assistant_text))

        people = [
            ExtractedPerson(
                display_name=name,
                relationship_type=self._guess_relationship_type(user_text),
                notes=f"Пользователь упомянул: {user_text[:500]}",
                importance=5 if re.search(r"\b(?:запомни|запиши)\b", user_text, re.I) else 3,
            )
            for name in names
        ]
        return ExtractionPayload(memories=memories, people=people)

    async def _persist(
        self,
        session: AsyncSession,
        user: User,
        user_text: str,
        payload: ExtractionPayload,
    ) -> None:
        now = datetime.now(timezone.utc)
        for memory in payload.memories:
            session.add(
                Memory(
                    user_id=user.id,
                    type=memory.type,
                    importance=memory.importance,
                    description=memory.description,
                )
            )

        for person_data in payload.people:
            normalized = person_data.display_name.casefold()
            person = await session.scalar(
                select(RelationshipPerson).where(
                    RelationshipPerson.user_id == user.id,
                    RelationshipPerson.normalized_name == normalized,
                )
            )
            if person is None:
                session.add(
                    RelationshipPerson(
                        user_id=user.id,
                        display_name=person_data.display_name,
                        normalized_name=normalized,
                        relationship_type=person_data.relationship_type,
                        importance=person_data.importance,
                        notes=person_data.notes,
                        last_mentioned_at=now,
                    )
                )
            else:
                person.notes = f"{person.notes or ''}\n{person_data.notes}".strip()
                person.last_mentioned_at = now
                person.importance = max(person.importance, person_data.importance)
                if person_data.relationship_type != "важный человек":
                    person.relationship_type = person_data.relationship_type

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
        for match in re.finditer(r"\*\*([А-ЯЁ][а-яё]{1,})\*\*", text):
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
