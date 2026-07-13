"""Нумерология Леи: классика + Матрица Судьбы."""

from __future__ import annotations

from datetime import date

from app.services.astrology.zodiac import zodiac_sign
from app.services.numerology.calculations import life_path_number, personal_year_number
from app.services.numerology.matrix import (
    arcana_label,
    arcana_of_year,
    destiny_matrix,
    patron_arcana,
)


class NumerologyService:
    def profile_context(self, *, name: str, birth: date, birth_city: str | None = None) -> str:
        lp = life_path_number(birth)
        py = personal_year_number(birth)
        sign, emoji = zodiac_sign(birth)
        matrix = destiny_matrix(birth)
        year_arc = arcana_of_year(birth)
        patron = patron_arcana(birth)
        city = birth_city or "не указано"
        return (
            f"Имя: {name}\n"
            f"Дата рождения: {birth.strftime('%d.%m.%Y')}\n"
            f"Место: {city}\n"
            f"Знак зодиака: {sign} {emoji}\n"
            f"Число жизненного пути: {lp}\n"
            f"Личное число года: {py}\n"
            f"Аркан года: {arcana_label(year_arc)}\n"
            f"Аркан-покровитель (по числу пути): {arcana_label(patron)}\n\n"
            "Матрица Судьбы (Хшановская):\n"
            + "\n".join(f"- {line}" for line in matrix.lines())
        )
