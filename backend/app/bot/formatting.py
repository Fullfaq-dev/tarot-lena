import re
from html import escape

_TELEGRAM_HTML_TAG = re.compile(r"</?(?:b|i|code|u|s|pre|blockquote)>", re.IGNORECASE)
_MD_TOKEN = re.compile(r"(\*\*.+?\*\*|\*.+?\*|`[^`]+`)", re.DOTALL)
_LONE_ANGLE = re.compile(r"<(?![/]?(?:b|i|code|u|s|pre|blockquote)\b)", re.IGNORECASE)


def to_telegram_html(text: str) -> str:
    """Конвертирует markdown от модели в HTML для Telegram."""
    if not text:
        return text

    # Модель иногда вставляет HTML-теги — убираем, чтобы не ломать парсер Telegram.
    cleaned = _TELEGRAM_HTML_TAG.sub("", text)
    cleaned = _LONE_ANGLE.sub("&lt;", cleaned)

    parts: list[str] = []
    last = 0
    for match in _MD_TOKEN.finditer(cleaned):
        parts.append(escape(cleaned[last : match.start()]))
        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            parts.append(f"<b>{escape(token[2:-2])}</b>")
        elif token.startswith("*") and token.endswith("*"):
            parts.append(f"<i>{escape(token[1:-1])}</i>")
        elif token.startswith("`") and token.endswith("`"):
            parts.append(f"<code>{escape(token[1:-1])}</code>")
        else:
            parts.append(escape(token))
        last = match.end()
    parts.append(escape(cleaned[last:]))
    return "".join(parts)
