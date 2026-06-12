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
        "супруг", "супруга", "супругу", "бывшая", "бывший", "конфликт", "помолвлен",
        "развод", "встречаюсь", "парень", "девушка",
    ],
    MemoryType.WORK.value: [
        "работаю", "работал", "работала", "бизнес", "клиент", "проект", "повышение",
        "уволился", "уволилась", "коллега", "начальник", "компания", "офис", "зарплат",
    ],
    MemoryType.MONEY.value: ["деньги", "долг", "кредит", "доход", "прибыль", "ипотек", "зарплат"],
    MemoryType.GOAL.value: ["цель", "планирую", "мечтаю", "хочу стать", "хочу переехать"],
}

_VALID_MEMORY_TYPES = {t.value for t in MemoryType}
_VALID_RELATIONSHIP_TYPES = {
    "семья", "дружба", "ребенок", "работа/бизнес", "бывшие отношения", "важный человек", "unknown",
}

_GREETING_ONLY = re.compile(
    r"^(?:привет|здравствуй(?:те)?|hi|hello|ку|йо|хай|добрый\s+(?:день|вечер|утро))[\s!.?]*$",
    re.IGNORECASE,
)

_BOT_SMALLTALK = re.compile(
    r"^(?:"
    r"(?:привет|здравствуй(?:те)?|hi|hello|ку|йо|хай|добрый\s+(?:день|вечер|утро))"
    r"[\s,!.?]*"
    r")?"
    r"(?:"
    r"работаешь|"
    r"ты\s+(?:тут|здесь|онлайн|на\s+связи|жив(?:ой|ая)?)|"
    r"на\s+связи|"
    r"слушаешь|"
    r"ты\s+тут|"
    r"как\s+дела|"
    r"что\s+нового|"
    r"ты\s+здесь"
    r")"
    r"[\s?.!]*$",
    re.IGNORECASE,
)

_BOT_QUESTION = re.compile(
    r"^(?:"
    r"(?:привет|здравствуй(?:те)?|hi|hello)[\s,!.?]*"
    r")?"
    r"(?:"
    r".*\b(?:работаешь|ты\s+тут|на\s+связи|как\s+дела|что\s+умеешь|ты\s+бот)\b"
    r")"
    r"[\s?.!]*$",
    re.IGNORECASE,
)

_EXPLICIT_REMEMBER = re.compile(r"\b(?:запомни|запиши)\b", re.IGNORECASE)

_EXTRACTION_SYSTEM = (
    "Ты анализируешь ОДНО сообщение пользователя эзотерическому боту в Telegram.\n"
    "Память — это долгосрочные факты о жизни пользователя, НЕ история переписки.\n\n"
    "СОХРАНЯЙ только стабильные факты:\n"
    "- родственники, партнёры, дети (имена, роли)\n"
    "- работа, бизнес, проекты\n"
    "- цели, планы, важные события\n"
    "- устойчивые предпочтения и обстоятельства\n\n"
    "НЕ СОХРАНЯЙ:\n"
    "- приветствия, «работаешь?», «ты тут?», проверки бота\n"
    "- вопросы к боту без фактов о жизни пользователя\n"
    "- просьбы сделать расклад, карту дня, толкование\n"
    "- эмоции момента без факта («устал сегодня»)\n"
    "- то, что уже было сказано ранее без новой информации\n\n"
    "Если пользователь просит «запомни» — сохрани только суть факта, без слова «запомни».\n"
    "importance: 5=критично, 4=важный факт, 3=полезный контекст. Не завышай.\n"
    "Если сомневаешься — верни пустые списки.\n"
    "Не выдумывай. Верни ТОЛЬКО валидный JSON без markdown:\n"
    '{"memories":[{"type":"relationship|work|money|goal|health|preference|event|other",'
    '"importance":3,"description":"краткий факт от третьего лица"}],'
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
        if self._is_noise_message(user_text):
            return None

        usage: dict[str, int] | None = None
        payload: ExtractionPayload | None = None

        if self._should_use_ai(user_text):
            payload, usage = await self._extract_with_ai(user_text, assistant_text)

        if payload is None:
            payload = self._extract_with_regex(user_text, assistant_text)

        payload = await self._filter_payload(session, user.id, user_text, payload)
        if payload.memories or payload.people:
            await self._persist(session, user, user_text, payload)

        return usage

    def _is_noise_message(self, user_text: str) -> bool:
        text = user_text.strip()
        if not text:
            return True
        if _GREETING_ONLY.match(text):
            return True
        if _BOT_SMALLTALK.match(text):
            return True
        if _BOT_QUESTION.match(text):
            return True
        return False

    def _should_use_ai(self, user_text: str) -> bool:
        text = user_text.strip()
        if len(text) < 12 and not _EXPLICIT_REMEMBER.search(text):
            return False
        if self._is_noise_message(text):
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
            importance = max(1, min(5, int(item.get("importance", 3))))
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
        if self._is_noise_message(user_text):
            return ExtractionPayload()

        memories: list[ExtractedMemory] = []
        explicit = self._extract_explicit_remember(user_text)
        if explicit:
            memories.append(explicit)

        names = self._extract_people(user_text)
        if _EXPLICIT_REMEMBER.search(user_text):
            names.update(self._extract_people_from_assistant(assistant_text))

        people = [
            ExtractedPerson(
                display_name=name,
                relationship_type=self._guess_relationship_type(user_text),
                notes=self._person_note(user_text, name),
                importance=5 if _EXPLICIT_REMEMBER.search(user_text) else 3,
            )
            for name in names
        ]
        return ExtractionPayload(memories=memories, people=people)

    def _extract_explicit_remember(self, user_text: str) -> ExtractedMemory | None:
        if not _EXPLICIT_REMEMBER.search(user_text):
            return None

        cleaned = re.sub(r"[\s\-—,]*(?:запомни|запиши)[\s!.?]*$", "", user_text, flags=re.I).strip()
        cleaned = re.sub(r"^(?:запомни|запиши)[\s\-—,:]*", "", cleaned, flags=re.I).strip()
        if len(cleaned) < 5 or self._is_noise_message(cleaned):
            return None

        memory_type = self._detect_memory_type(cleaned) or MemoryType.OTHER.value
        return ExtractedMemory(type=memory_type, importance=5, description=cleaned[:1000])

    async def _filter_payload(
        self,
        session: AsyncSession,
        user_id: str,
        user_text: str,
        payload: ExtractionPayload,
    ) -> ExtractionPayload:
        explicit = bool(_EXPLICIT_REMEMBER.search(user_text))
        memories: list[ExtractedMemory] = []
        for memory in payload.memories:
            if not self._is_worth_persisting(memory.description, explicit=explicit):
                continue
            if await self._is_duplicate_memory(session, user_id, memory.description):
                continue
            memories.append(memory)

        people: list[ExtractedPerson] = []
        seen_names: set[str] = set()
        for person in payload.people:
            key = person.display_name.casefold()
            if key in seen_names:
                continue
            seen_names.add(key)
            people.append(person)

        return ExtractionPayload(memories=memories, people=people)

    def _is_worth_persisting(self, description: str, *, explicit: bool) -> bool:
        text = description.strip()
        if len(text) < 8:
            return explicit
        if self._is_noise_message(text):
            return False
        if _BOT_QUESTION.match(text):
            return False
        if not explicit and text.endswith("?") and len(text) < 80:
            return False
        if not explicit and re.fullmatch(r"[\W\d\s]+", text):
            return False
        return True

    async def _is_duplicate_memory(
        self, session: AsyncSession, user_id: str, description: str
    ) -> bool:
        normalized = self._normalize_for_dedup(description)
        if not normalized:
            return True

        existing = await session.scalars(
            select(Memory).where(Memory.user_id == user_id, Memory.is_active.is_(True))
        )
        for memory in existing:
            existing_norm = self._normalize_for_dedup(memory.description)
            if existing_norm == normalized:
                return True
            if len(normalized) >= 12 and (
                normalized in existing_norm or existing_norm in normalized
            ):
                return True
        return False

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
            if any(self._contains_word(lower, marker) for marker in markers):
                return memory_type
        return None

    def _contains_word(self, text: str, word: str) -> bool:
        return (
            re.search(rf"(?<![а-яёa-z]){re.escape(word)}", text, re.IGNORECASE) is not None
        )

    def _person_note(self, user_text: str, name: str) -> str:
        if _EXPLICIT_REMEMBER.search(user_text):
            cleaned = re.sub(r"\b(?:запомни|запиши)\b", "", user_text, flags=re.I).strip(" -—,.")
            return cleaned[:500] if cleaned else f"Имя: {name}"
        return f"Упомянут в диалоге: {user_text[:300]}"

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

    def _normalize_for_dedup(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text.casefold().strip())
        cleaned = re.sub(r"[!.?…]+$", "", cleaned)
        return cleaned

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
