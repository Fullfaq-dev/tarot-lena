import re
from html import escape


def to_telegram_html(text: str) -> str:
    """Конвертирует базовый markdown от модели в HTML для Telegram."""
    if not text:
        return text

    if re.search(r"</?(?:b|i|code|u|s)>", text):
        return text

    parts: list[str] = []
    last = 0
    for match in re.finditer(r"(\*\*.+?\*\*|\*.+?\*|`[^`]+`)", text, flags=re.DOTALL):
        parts.append(escape(text[last : match.start()]))
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
    parts.append(escape(text[last:]))
    return "".join(parts)
