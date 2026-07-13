from pathlib import Path

from app.services.ai.context import load_system_prompt

_PROMPTS_DIR = Path(__file__).resolve().parents[4] / "prompts"


def _load(name: str) -> str:
    path = _PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def numerology_system() -> str:
    base = load_system_prompt("ru")
    extra = _load("numerology_ru.md")
    return f"{base}\n\n{extra}" if extra else base


def astro_system() -> str:
    base = load_system_prompt("ru")
    extra = _load("astro_ru.md")
    return f"{base}\n\n{extra}" if extra else base


def tarot_system() -> str:
    base = load_system_prompt("ru")
    extra = _load("tarot_ru.md")
    return f"{base}\n\n{extra}" if extra else base


def leia_reading_system() -> str:
    parts = [numerology_system(), _load("tarot_ru.md"), _load("astro_ru.md")]
    return "\n\n".join(p for p in parts if p)
