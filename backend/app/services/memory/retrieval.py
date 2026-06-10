import re

from app.database.models import Memory, RelationshipPerson

_STOPWORDS = {
    "это",
    "как",
    "что",
    "или",
    "для",
    "при",
    "над",
    "под",
    "мне",
    "меня",
    "тебя",
    "твой",
    "мой",
    "моя",
    "моей",
    "был",
    "была",
    "было",
    "были",
    "есть",
    "если",
    "когда",
    "почему",
    "зачем",
    "очень",
    "просто",
    "сейчас",
    "сегодня",
    "завтра",
    "вчера",
    "можно",
    "нужно",
    "хочу",
    "хотел",
    "скажи",
    "расскажи",
    "помоги",
    "подскажи",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[а-яёa-z]{3,}", (text or "").lower())
    return {word for word in words if word not in _STOPWORDS}


def _overlap_score(query: str, text: str) -> int:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0
    haystack = (text or "").lower()
    score = 0
    for token in query_tokens:
        if token in haystack:
            score += 2 if len(token) >= 5 else 1
    return score


def select_relevant_memories(query: str, memories: list[Memory], *, limit: int = 3) -> list[Memory]:
    scored = [
        (memory, _overlap_score(query, memory.description))
        for memory in memories
    ]
    relevant = [memory for memory, score in scored if score >= 2]
    if not relevant:
        return []
    relevant.sort(key=lambda memory: _overlap_score(query, memory.description), reverse=True)
    return relevant[:limit]


def select_relevant_people(
    query: str, people: list[RelationshipPerson], *, limit: int = 2
) -> list[RelationshipPerson]:
    query_lower = (query or "").lower()
    scored: list[tuple[RelationshipPerson, int]] = []
    for person in people:
        score = 0
        name = (person.display_name or "").strip().lower()
        for part in name.split():
            if len(part) >= 3 and part in query_lower:
                score += 5
        score += _overlap_score(query, person.notes or "")
        score += _overlap_score(query, person.relationship_type or "")
        if score >= 3:
            scored.append((person, score))
    if not scored:
        return []
    scored.sort(key=lambda item: item[1], reverse=True)
    return [person for person, _ in scored[:limit]]
