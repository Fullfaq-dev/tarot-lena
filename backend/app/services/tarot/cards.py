from __future__ import annotations

from pathlib import Path

RANK_NAMES: dict[int, str] = {
    1: "Туз",
    2: "Двойка",
    3: "Тройка",
    4: "Четвёрка",
    5: "Пятёрка",
    6: "Шестёрка",
    7: "Семёрка",
    8: "Восьмёрка",
    9: "Девятка",
    10: "Десятка",
    11: "Паж",
    12: "Рыцарь",
    13: "Королева",
    14: "Король",
}

RANK_THEMES: dict[int, str] = {
    1: "начало, потенциал, импульс",
    2: "партнёрство, выбор, баланс",
    3: "рост, общение, первые плоды",
    4: "стабильность, пауза, основа",
    5: "напряжение, испытание, сдвиг",
    6: "гармония, помощь, восстановление",
    7: "стратегия, терпение, проверка",
    8: "движение, сила, ускорение",
    9: "завершение этапа, накопленный опыт",
    10: "итог цикла, нагрузка, ответственность",
    11: "ученик, любопытство, первые шаги",
    12: "действие, движение, импульс",
    13: "зрелость, забота, внутренняя сила",
    14: "мастерство, стабильность, ответственность",
}

SUIT_CONFIG: dict[str, dict[str, str]] = {
    "Cups": {"slug": "cups", "name": "Кубки", "theme": "чувства, отношения, интуиция"},
    "Wands": {"slug": "wands", "name": "Жезлы", "theme": "воля, творчество, действие"},
    "Swords": {"slug": "swords", "name": "Мечи", "theme": "разум, конфликт, ясность"},
    "Pentacles": {"slug": "pentacles", "name": "Пентакли", "theme": "материя, работа, ресурсы"},
}

MAJOR_ARCANA: list[dict[str, str | int]] = [
    {"number": 0, "slug": "fool", "name": "Шут", "description": "новый путь, спонтанность, доверие жизни", "image_file": "00-TheFool.jpg"},
    {"number": 1, "slug": "magician", "name": "Маг", "description": "воля, действие, способность влиять", "image_file": "01-TheMagician.jpg"},
    {"number": 2, "slug": "high_priestess", "name": "Жрица", "description": "интуиция, тайна, внутреннее знание", "image_file": "02-TheHighPriestess.jpg"},
    {"number": 3, "slug": "empress", "name": "Императрица", "description": "рост, тело, забота, ресурс", "image_file": "03-TheEmpress.jpg"},
    {"number": 4, "slug": "emperor", "name": "Император", "description": "структура, ответственность, власть", "image_file": "04-TheEmperor.jpg"},
    {"number": 5, "slug": "hierophant", "name": "Иерофант", "description": "традиция, наставник, духовный закон", "image_file": "05-TheHierophant.jpg"},
    {"number": 6, "slug": "lovers", "name": "Влюбленные", "description": "выбор, союз, ценности сердца", "image_file": "06-TheLovers.jpg"},
    {"number": 7, "slug": "chariot", "name": "Колесница", "description": "движение, победа, управление силой", "image_file": "07-TheChariot.jpg"},
    {"number": 8, "slug": "strength", "name": "Сила", "description": "мягкая власть, смелость, внутренний зверь", "image_file": "08-Strength.jpg"},
    {"number": 9, "slug": "hermit", "name": "Отшельник", "description": "поиск смысла, пауза, мудрость", "image_file": "09-TheHermit.jpg"},
    {"number": 10, "slug": "wheel_of_fortune", "name": "Колесо Фортуны", "description": "цикл, шанс, поворот судьбы", "image_file": "10-WheelOfFortune.jpg"},
    {"number": 11, "slug": "justice", "name": "Справедливость", "description": "баланс, честность, последствия выбора", "image_file": "11-Justice.jpg"},
    {"number": 12, "slug": "hanged_man", "name": "Повешенный", "description": "смена взгляда, пауза, принятие", "image_file": "12-TheHangedMan.jpg"},
    {"number": 13, "slug": "death", "name": "Смерть", "description": "завершение, трансформация, освобождение", "image_file": "13-Death.jpg"},
    {"number": 14, "slug": "temperance", "name": "Умеренность", "description": "исцеление, мера, гармонизация", "image_file": "14-Temperance.jpg"},
    {"number": 15, "slug": "devil", "name": "Дьявол", "description": "привязки, соблазн, скрытая зависимость", "image_file": "15-TheDevil.jpg"},
    {"number": 16, "slug": "tower", "name": "Башня", "description": "слом старого, правда, резкая перестройка", "image_file": "16-TheTower.jpg"},
    {"number": 17, "slug": "star", "name": "Звезда", "description": "надежда, вдохновение, дальняя цель", "image_file": "17-TheStar.jpg"},
    {"number": 18, "slug": "moon", "name": "Луна", "description": "страхи, сны, туман, подсознание", "image_file": "18-TheMoon.jpg"},
    {"number": 19, "slug": "sun", "name": "Солнце", "description": "радость, ясность, успех, жизнь", "image_file": "19-TheSun.jpg"},
    {"number": 20, "slug": "judgement", "name": "Суд", "description": "пробуждение, зов, важное решение", "image_file": "20-Judgement.jpg"},
    {"number": 21, "slug": "world", "name": "Мир", "description": "завершение цикла, целостность, результат", "image_file": "21-TheWorld.jpg"},
]

CARD_BACK_IMAGE = "CardBacks.jpg"


def _minor_arcana() -> list[dict[str, str | int]]:
    cards: list[dict[str, str | int]] = []
    for prefix, config in SUIT_CONFIG.items():
        suit_name = config["name"]
        suit_slug = config["slug"]
        theme = config["theme"]
        for number in range(1, 15):
            rank = RANK_NAMES[number]
            if number == 1:
                name = f"Туз {suit_name}"
            else:
                name = f"{rank} {suit_name}"
            cards.append(
                {
                    "number": number,
                    "slug": f"{suit_slug}_{number:02d}",
                    "name": name,
                    "description": f"{theme}; {RANK_THEMES[number]}",
                    "arcana": "minor",
                    "suit": suit_slug,
                    "image_file": f"{prefix}{number:02d}.jpg",
                }
            )
    return cards


MINOR_ARCANA: list[dict[str, str | int]] = _minor_arcana()
FULL_DECK: list[dict[str, str | int]] = [
    {**card, "arcana": "major"} for card in MAJOR_ARCANA
] + MINOR_ARCANA


def image_path_for(card: dict[str, str | int], cards_dir: Path) -> str:
    return str(cards_dir / str(card["image_file"]))


def storage_image_path(card: dict[str, str | int], cards_dir: Path) -> str:
    return image_path_for(card, cards_dir)
