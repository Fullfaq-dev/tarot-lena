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
