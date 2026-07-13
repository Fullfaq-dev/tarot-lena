"""Астрология Леи — тропический зодиак."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.astrology.zodiac import zodiac_sign


class AstrologyService:
    def sign_label(self, birth: date) -> tuple[str, str]:
        return zodiac_sign(birth)

    def week_range_label(self, for_day: date) -> str:
        monday = for_day - timedelta(days=for_day.weekday())
        sunday = monday + timedelta(days=6)
        return f"{monday.strftime('%d.%m')} — {sunday.strftime('%d.%m')}"
