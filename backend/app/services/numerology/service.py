"""Нумерология Леи: классика + Матрица Судьбы."""

from __future__ import annotations

from datetime import date

from app.services.astrology.zodiac import zodiac_sign
from app.services.numerology.calculations import (
    life_path_number,
    personal_day_number,
    personal_month_number,
    personal_year_number,
)
from app.services.numerology.matrix import (
    arcana_label,
    arcana_of_month,
    arcana_of_year,
    destiny_matrix,
    patron_arcana,
    week_arcana_number,
)


class NumerologyService:
    def profile_context(self, *, name: str, birth: date, birth_city: str | None = None) -> str:
        vars_ = self.prompt_vars(name=name, birth=birth, birth_city=birth_city)
        return (
            f"Имя: {vars_['name']}\n"
            f"Дата рождения: {vars_['bd']}\n"
            f"Место: {vars_.get('city', 'не указано')}\n"
            f"Знак зодиака: {vars_['sign']}\n"
            f"Число жизненного пути: {vars_['life_path']}\n"
            f"Личное число года: {vars_['year_num']}\n"
            f"Аркан года: {vars_['year_arcana']}\n"
            f"Аркан-покровитель (по числу пути): {arcana_label(patron_arcana(birth))}\n\n"
            "Матрица Судьбы (Хшановская):\n"
            f"{vars_['matrix']}"
        )

    def prompt_vars(
        self,
        *,
        name: str,
        birth: date | None,
        birth_city: str | None = None,
        for_day: date | None = None,
        partner_bd: str = "",
        question: str = "",
        cards: str = "",
        last_7: str = "",
        sign_forecast: str = "",
        dates: str = "",
    ) -> dict[str, str | int]:
        """Готовые цифры для блоков промпта — модель ничего не считает."""
        day = for_day or date.today()
        vars_: dict[str, str | int] = {
            "name": name or "ты",
            "bd": "—",
            "sign": "—",
            "date": day.strftime("%d.%m.%Y"),
            "life_path": "—",
            "personal_day": "—",
            "personal_month": "—",
            "year_num": "—",
            "year_arcana": "—",
            "week_arcana": "—",
            "month_arcana": "—",
            "partner_bd": partner_bd or "—",
            "question": question or "—",
            "cards": cards or "—",
            "last_7": last_7 or "нет",
            "sign_forecast": sign_forecast or "",
            "dates": dates or "",
            "matrix": "",
            "city": birth_city or "не указано",
        }
        if birth is None:
            return vars_

        sign, emoji = zodiac_sign(birth)
        lp = life_path_number(birth)
        py = personal_year_number(birth, day.year)
        pm = personal_month_number(birth, day)
        pd = personal_day_number(birth, day)
        ya = arcana_of_year(birth, day.year)
        ma = arcana_of_month(birth, day)
        wa = week_arcana_number(birth, day)
        matrix = destiny_matrix(birth)

        vars_.update(
            {
                "bd": birth.strftime("%d.%m.%Y"),
                "sign": f"{sign} {emoji}",
                "life_path": lp,
                "personal_day": pd,
                "personal_month": pm,
                "year_num": py,
                "year_arcana": arcana_label(ya),
                "month_arcana": arcana_label(ma),
                "week_arcana": arcana_label(wa),
                "matrix": "\n".join(f"- {line}" for line in matrix.lines()),
            }
        )
        return vars_
