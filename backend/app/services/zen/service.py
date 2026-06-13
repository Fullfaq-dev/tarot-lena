from __future__ import annotations

import random
from pathlib import Path

from app.bot.i18n import normalize_language, t

_PROMPT_DIR = Path(__file__).resolve().parents[4] / "prompts"

DAILY_PROMPTS: dict[str, list[str]] = {
    "ru": [
        "Что сегодня ты замечаешь в себе без оценки — просто как факт?",
        "Где в теле сейчас живёт напряжение, и что оно хочет сказать?",
        "Если убрать желание «правильного» ответа — что остаётся?",
        "Какой один маленький шаг к себе возможен сегодня?",
        "Что ты готов отпустить, не зная, чем это заполнится?",
    ],
    "en": [
        "What do you notice in yourself today without judging — just as a fact?",
        "Where does tension live in your body right now, and what might it be saying?",
        "If you drop the need for a 'right' answer — what remains?",
        "What one small step toward yourself is possible today?",
        "What are you willing to release without knowing what will fill the space?",
    ],
    "es": [
        "¿Qué notas en ti hoy sin juzgar — solo como un hecho?",
        "¿Dónde vive la tensión en tu cuerpo ahora y qué podría decirte?",
        "Si sueltas la necesidad de la respuesta 'correcta' — ¿qué queda?",
        "¿Qué pequeño paso hacia ti es posible hoy?",
        "¿Qué estás dispuesto a soltar sin saber con qué se llenará?",
    ],
    "pt": [
        "O que você percebe em si hoje sem julgar — apenas como fato?",
        "Onde a tensão mora no seu corpo agora e o que ela pode estar dizendo?",
        "Se você largar a necessidade da resposta 'certa' — o que resta?",
        "Qual pequeno passo em direção a si é possível hoje?",
        "O que você está disposto a soltar sem saber o que preencherá o espaço?",
    ],
}


class ZenService:
    def daily_prompt(self, lang: str = "ru") -> str:
        lang = normalize_language(lang)
        prompts = DAILY_PROMPTS.get(lang) or DAILY_PROMPTS["ru"]
        return random.choice(prompts)

    def load_zen_prompt(self, lang: str = "ru") -> str:
        lang = normalize_language(lang)
        path = _PROMPT_DIR / f"zen_{lang}.md"
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        fallback = _PROMPT_DIR / "zen_ru.md"
        if fallback.exists():
            return fallback.read_text(encoding="utf-8").strip()
        return t("zen_default_system", lang)

    def reflection_intro(self, lang: str = "ru") -> str:
        return t("zen_reflection_intro", lang)

    def daily_intro(self, lang: str = "ru") -> str:
        return t("zen_daily_intro", lang)
