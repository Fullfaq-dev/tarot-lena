import re
from html import escape, unescape

_TELEGRAM_HTML_TAG = re.compile(r"</?(?:b|i|code|u|s|pre|blockquote)>", re.IGNORECASE)
_MD_TOKEN = re.compile(r"(\*\*.+?\*\*|\*.+?\*|`[^`]+`)", re.DOTALL)
_LONE_ANGLE = re.compile(r"<(?![/]?(?:b|i|code|u|s|pre|blockquote)\b)", re.IGNORECASE)
_RICH_STRIP_HTML = re.compile(
    r"</?(?:script|style|iframe|object|embed|form|input|button|meta|link)\b[^>]*>",
    re.IGNORECASE,
)

_PRE_BLOCK = re.compile(r"<pre>(.*?)</pre>", re.IGNORECASE | re.DOTALL)
_CODE_INLINE = re.compile(r"<code>(.*?)</code>", re.IGNORECASE | re.DOTALL)
_LINK = re.compile(r"""<a\s+href=["']?(.*?)["']?\s*>(.*?)</a>""", re.IGNORECASE | re.DOTALL)
_BOLD = re.compile(r"<\s*(?:b|strong)\s*>(.*?)<\s*/\s*(?:b|strong)\s*>", re.IGNORECASE | re.DOTALL)
_ITALIC = re.compile(r"<\s*(?:i|em)\s*>(.*?)<\s*/\s*(?:i|em)\s*>", re.IGNORECASE | re.DOTALL)
_STRIKE = re.compile(r"<\s*(?:s|strike|del)\s*>(.*?)<\s*/\s*(?:s|strike|del)\s*>", re.IGNORECASE | re.DOTALL)
_BLOCKQUOTE = re.compile(r"<blockquote>(.*?)</blockquote>", re.IGNORECASE | re.DOTALL)
_REMAINING_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_HEADING_LINE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")


def _blockquote_to_markdown(inner: str) -> str:
    inner = inner.strip("\n")
    lines = inner.split("\n")
    return "\n".join(f"> {line}" if line.strip() else ">" for line in lines)


def html_to_rich_markdown(text: str) -> str:
    """Convert the Telegram-HTML used in bot panels into rich markdown.

    Section titles (whole-line bold) become headings, <pre> turns into
    preformatted blocks, and inline formatting maps to markdown so panels
    render through the rich message pipeline just like readings do.
    """
    if not text:
        return text

    s = text.replace("\r\n", "\n")

    pre_blocks: list[str] = []

    def _stash_pre(match: re.Match) -> str:
        inner = unescape(_REMAINING_TAG.sub("", match.group(1))).strip("\n")
        pre_blocks.append(f"```\n{inner}\n```")
        return f"\x00PRE{len(pre_blocks) - 1}\x00"

    s = _PRE_BLOCK.sub(_stash_pre, s)
    s = _BLOCKQUOTE.sub(lambda m: _blockquote_to_markdown(m.group(1)), s)
    s = _LINK.sub(lambda m: f"[{m.group(2).strip()}]({m.group(1).strip()})", s)
    s = _CODE_INLINE.sub(lambda m: f"`{m.group(1).strip()}`", s)
    s = _BOLD.sub(lambda m: f"**{m.group(1).strip()}**", s)
    s = _ITALIC.sub(lambda m: f"*{m.group(1).strip()}*", s)
    s = _STRIKE.sub(lambda m: f"~~{m.group(1).strip()}~~", s)

    s = _REMAINING_TAG.sub("", s)
    s = unescape(s)

    out_lines: list[str] = []
    for line in s.split("\n"):
        heading = _HEADING_LINE.match(line)
        if heading:
            out_lines.append(f"### {heading.group(1).strip()}")
        else:
            out_lines.append(line)
    s = "\n".join(out_lines)

    for index, block in enumerate(pre_blocks):
        s = s.replace(f"\x00PRE{index}\x00", block)

    return s.strip()


def prepare_rich_markdown(text: str) -> str:
    """Prepare model output for Telegram rich markdown."""
    if not text:
        return text
    cleaned = _RICH_STRIP_HTML.sub("", text)
    return cleaned.replace("\r\n", "\n").strip()


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
