"""Матрица Судьбы (метод Наталии Ладини / Хшановской) — расчёт арканов 1–22."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.services.numerology.calculations import life_path_number, personal_year_number

MAJOR_ARCANA: dict[int, tuple[str, str]] = {
    1: ("Маг", "воля, действие, старт"),
    2: ("Жрица", "интуиция, тайна, глубина"),
    3: ("Императрица", "рост, забота, изобилие"),
    4: ("Император", "структура, опора, ответственность"),
    5: ("Иерофант", "традиция, наставник, знание"),
    6: ("Влюблённые", "выбор, союз, сердце"),
    7: ("Колесница", "движение, победа, цель"),
    8: ("Сила", "смелость, внутренняя мощь"),
    9: ("Отшельник", "мудрость, пауза, поиск"),
    10: ("Колесо Фортуны", "цикл, перемены, шанс"),
    11: ("Справедливость", "баланс, честность, выбор"),
    12: ("Повешенный", "новый взгляд, принятие"),
    13: ("Смерть", "трансформация, завершение"),
    14: ("Умеренность", "гармония, исцеление"),
    15: ("Дьявол", "привязки, соблазны, сила тени"),
    16: ("Башня", "перелом, правда, обновление"),
    17: ("Звезда", "надежда, вдохновение"),
    18: ("Луна", "интуиция, сны, чувствительность"),
    19: ("Солнце", "радость, ясность, успех"),
    20: ("Суд", "пробуждение, важное решение"),
    21: ("Мир", "целостность, результат"),
    22: ("Шут", "новый путь, свобода, доверие"),
}


def arcana_reduce(value: int) -> int:
    n = abs(int(value))
    while n > 22:
        n = sum(int(d) for d in str(n))
    return 22 if n == 0 else n


def arcana_label(n: int) -> str:
    num = arcana_reduce(n)
    name, meaning = MAJOR_ARCANA[num]
    return f"{name} — {meaning}"


def arcana_name(n: int) -> str:
    return MAJOR_ARCANA[arcana_reduce(n)][0]


def arcana_meaning(n: int) -> str:
    return MAJOR_ARCANA[arcana_reduce(n)][1]


@dataclass(frozen=True)
class DestinyMatrix:
    birth: date
    day: int
    month: int
    year: int
    soul: int
    personality: int
    comfort: int
    social: int
    talent: int
    purpose: int

    def lines(self) -> list[str]:
        return [
            f"Аркан дня рождения: {arcana_label(self.day)}",
            f"Аркан месяца: {arcana_label(self.month)}",
            f"Аркан года рождения: {arcana_label(self.year)}",
            f"Аркан души (центр): {arcana_label(self.soul)}",
            f"Личность: {arcana_label(self.personality)}",
            f"Зона комфорта: {arcana_label(self.comfort)}",
            f"Социальное: {arcana_label(self.social)}",
            f"Талант: {arcana_label(self.talent)}",
            f"Предназначение: {arcana_label(self.purpose)}",
        ]

    def table_rows(self) -> list[list[str]]:
        return [
            ["День", arcana_label(self.day)],
            ["Месяц", arcana_label(self.month)],
            ["Год", arcana_label(self.year)],
            ["Душа", arcana_label(self.soul)],
            ["Предназначение", arcana_label(self.purpose)],
        ]


def destiny_matrix(birth: date) -> DestinyMatrix:
    day = arcana_reduce(birth.day)
    month = arcana_reduce(birth.month)
    year = arcana_reduce(sum(int(c) for c in str(birth.year)))
    soul = arcana_reduce(day + month + year)
    personality = arcana_reduce(day + month)
    comfort = arcana_reduce(month + year)
    social = arcana_reduce(day + year)
    talent = arcana_reduce(personality + comfort)
    purpose = arcana_reduce(day + year + soul)
    return DestinyMatrix(
        birth=birth,
        day=day,
        month=month,
        year=year,
        soul=soul,
        personality=personality,
        comfort=comfort,
        social=social,
        talent=talent,
        purpose=purpose,
    )


def arcana_of_year(birth: date, year: int | None = None) -> int:
    py = personal_year_number(birth, year)
    return arcana_reduce(py)


def patron_arcana(birth: date) -> int:
    lp = life_path_number(birth)
    return arcana_reduce(lp)


def weekly_patron_arcana(birth: date, for_day: date) -> tuple[str, str]:
    week = for_day.isocalendar().week
    num = arcana_reduce(week + birth.day + birth.month)
    return arcana_name(num), arcana_meaning(num)
