"""Генерация мини-разбора одним JSON-запросом."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date
from pathlib import Path

from app.services.web.catalog import WebCard
from app.services.web.fragments import MIRROR
from app.services.web.mini import build_mini
from app.services.web.mini_spec import card_accusative, life_path_word, spec_for

logger = logging.getLogger(__name__)

_PROMPTS = Path(__file__).resolve().parents[4] / "prompts" / "leia" / "web_mini.md"
_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)
PENDING_COPY = "Лея дописывает разбор, загляни через минуту"
MINI_TIMEOUT_SEC = 15.0


def _core_mini() -> str:
    if _PROMPTS.exists():
        return _PROMPTS.read_text(encoding="utf-8").strip()
    return "Ты Лея. Верни JSON мини-разбора: verdict, body, hook, paywall_title, paywall_bullets."


def parse_mini_json(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    raw = _JSON_FENCE.sub("", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _clip(value: object, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    clipped = text[: limit - 1].rstrip(" .,;:—–-")
    return clipped + "…"


def _as_paragraphs(value: object) -> list[str]:
    if isinstance(value, str):
        parts = [item.strip() for item in re.split(r"\n{2,}", value) if item.strip()]
        return parts[:2]
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return parts[:2]
    return []


def _q3_label(card_id: str, answers: list[str]) -> str:
    spec = MIRROR.get(card_id) or {}
    q3 = answers[2] if len(answers) > 2 else ""
    mapping = spec.get("q3") or {}
    return str(mapping.get(q3) or q3)


def _format_ctx(card: WebCard, answers: list[str], shell: dict) -> dict[str, str]:
    names = [str(block.get("name") or "") for block in shell.get("blocks") or []]
    names = [name for name in names if name]
    q1 = answers[0] if answers else ""
    q2 = answers[1] if len(answers) > 1 else ""
    q3 = answers[2] if len(answers) > 2 else ""
    stats = shell.get("stats") or {}
    c1 = names[0] if names else "карта"
    c2 = names[1] if len(names) > 1 else c1
    c3 = names[2] if len(names) > 2 else (names[-1] if names else "карта")
    soon_q3 = {"Месяц": "месяц", "Три месяца": "три месяца", "Полгода": "полгода"}.get(q3, q3.lower())
    return {
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "c2_acc": card_accusative(c2),
        "c3_acc": card_accusative(c3),
        "q1": q1,
        "q2": q2,
        "q3": _q3_label(card.id, answers) if card.id != "soon" else soon_q3,
        "life_path_word": life_path_word(stats.get("life_path")),
    }


def _fmt(template: str, ctx: dict[str, str]) -> str:
    try:
        return template.format(**ctx)
    except (KeyError, IndexError):
        return template


def _valid_title(value: str, *, require_uznai: bool) -> bool:
    text = value.strip()
    if not text or len(text) > 45:
        return False
    if require_uznai and not text.startswith("Узнай"):
        return False
    return True


def _valid_bullets(value: object) -> list[str] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    items = [_clip(item, 55) for item in value]
    if any(len(item) < 4 for item in items):
        return None
    return items


def apply_generated(card: WebCard, answers: list[str], shell: dict, payload: dict) -> dict:
    spec = spec_for(card.id)
    ctx = _format_ctx(card, answers, shell)
    verdict = _clip(payload.get("verdict"), 200)
    body = _as_paragraphs(payload.get("body"))
    hook = str(payload.get("hook") or "").strip()
    mini = dict(shell)
    mini["source"] = "ai"
    mini["pending"] = False
    mini["fade"] = False
    mini["verdict"] = verdict
    mini["body"] = body
    mini["hook"] = hook
    mini["lead"] = verdict or mini.get("lead") or ""
    mini["mirror"] = verdict or mini.get("mirror") or ""
    mini["cut"] = hook
    mini["cta"] = _fmt(spec.cta, ctx) if spec.cta else mini.get("cta")
    if spec.paywall_title_static:
        mini["paywall_title"] = spec.paywall_title_static
    else:
        title = str(payload.get("paywall_title") or "").strip()
        mini["paywall_title"] = title if _valid_title(title, require_uznai=True) else _fmt(spec.fallback_title, ctx)
    bullets = _valid_bullets(payload.get("paywall_bullets"))
    mini["paywall_bullets"] = bullets or [_fmt(item, ctx) for item in spec.fallback_bullets]
    question = _clip(payload.get("question_example"), 50)
    mini["question_example"] = question or spec.fallback_question
    tg_q = _clip(payload.get("tg_question_example"), 50)
    mini["tg_question_example"] = tg_q or spec.fallback_question
    if card.price_rub == 0:
        mini["paywall_title"] = ""
        mini["paywall_bullets"] = []
        mini["free"] = True
    return mini


def pending_mini(shell: dict) -> dict:
    mini = dict(shell)
    mini.update(
        {
            "source": "pending",
            "pending": True,
            "fade": False,
            "verdict": "",
            "body": [],
            "hook": "",
            "lead": "",
            "mirror": "",
            "cut": PENDING_COPY,
            "paywall_title": "",
            "paywall_bullets": [],
        }
    )
    return mini


def _user_payload(
    card: WebCard,
    answers: list[str],
    *,
    drawn: list[dict] | None,
    birth: date | None,
    partner_birth: date | None,
    shell: dict,
) -> str:
    spec = spec_for(card.id)
    names = []
    for index, item in enumerate(drawn or []):
        position = card.positions[index] if index < len(card.positions) else f"Карта {index + 1}"
        names.append(f"{position}: {item.get('name')} ({item.get('description') or ''})")
    stats = shell.get("stats") or {}
    nums = ""
    if birth is not None:
        from app.services.numerology.service import NumerologyService

        vars_ = NumerologyService().prompt_vars(
            name="ты",
            birth=birth,
            partner_bd=partner_birth.strftime("%d.%m.%Y") if partner_birth else "",
        )
        nums = (
            f"Число пути: {vars_.get('life_path')}\n"
            f"Знак: {vars_.get('sign')}\n"
            f"Аркан года: {vars_.get('year_arcana')}\n"
        )
        if card.branch == "date":
            nums += f"Матрица:\n{vars_.get('matrix')}\n"
        if card.branch == "pair" and stats:
            nums += (
                f"Число пути партнёра: {stats.get('partner_life_path')}\n"
                f"Знак партнёра: {stats.get('partner_sign')}\n"
                f"Стихии: {stats.get('elements')}\n"
                f"Совместимость (уже посчитана, в текст не писать): {stats.get('percent')}%\n"
            )
    lines = [
        f"ПРОДУКТ: {card.product_name}",
        f"КАРТОЧКА: {card.title} ({card.id})",
        f"ПРАВИЛО: {spec.rule}",
        f"ОТКРЫТЬ: {spec.interpret}",
        f"ОТВЕТЫ КВИЗА: {answers}",
    ]
    if names:
        lines.append("КАРТЫ:\n" + "\n".join(names))
    if birth:
        lines.append(f"ДАТА: {birth.strftime('%d.%m.%Y')}")
    if partner_birth:
        lines.append(f"ДАТА ПАРТНЁРА: {partner_birth.strftime('%d.%m.%Y')}")
    if nums:
        lines.append(nums.strip())
    if spec.paywall_title_static:
        lines.append("paywall_title не заполняй.")
    if card.price_rub == 0:
        lines.append("Экрана оплаты нет. paywall-поля оставь пустыми строками и пустым массивом.")
    return "\n".join(lines)


async def generate_ai_mini(
    card: WebCard,
    answers: list[str],
    *,
    drawn: list[dict] | None = None,
    birth: date | None = None,
    partner_birth: date | None = None,
    shell: dict | None = None,
) -> dict:
    shell = shell or build_mini(card, answers, drawn=drawn, birth=birth, partner_birth=partner_birth)
    if card.id == "daily":
        shell["source"] = "library"
        shell["pending"] = False
        shell["fade"] = False
        shell["verdict"] = str(shell.get("mirror") or "")
        body = []
        for block in shell.get("blocks") or []:
            text = str(block.get("text") or "").replace("**", "")
            if text:
                body.append(text)
        shell["body"] = body
        shell["hook"] = str(shell.get("cut") or "")
        shell["lead"] = shell["verdict"]
        return shell

    spec = spec_for(card.id)
    from app.core.config import get_settings
    from app.services.ai.kie_client import KieClient

    settings = get_settings()
    client = KieClient()
    messages = [
        {"role": "system", "content": _core_mini()},
        {
            "role": "user",
            "content": _user_payload(
                card, answers, drawn=drawn, birth=birth, partner_birth=partner_birth, shell=shell
            ),
        },
    ]
    last_error: Exception | None = None
    for attempt in range(2):
        effort = "none" if attempt == 0 else "low"
        try:
            text = await asyncio.wait_for(
                client.chat_completion(
                    messages,
                    reasoning_effort=effort,
                    model=settings.openai_mini_model,
                    max_output_tokens=spec.max_tokens,
                    timeout=MINI_TIMEOUT_SEC,
                    max_attempts=1,
                ),
                timeout=MINI_TIMEOUT_SEC + 1,
            )
            parsed = parse_mini_json(text)
            if parsed and str(parsed.get("verdict") or "").strip():
                mini = apply_generated(card, answers, shell, parsed)
                mini["usage"] = client.last_usage
                return mini
            last_error = ValueError("empty or invalid mini json")
        except Exception as exc:
            last_error = exc
            logger.warning("web mini generation failed card=%s attempt=%s: %s", card.id, attempt + 1, exc)
    logger.warning("web mini fallback pending card=%s error=%s", card.id, last_error)
    pending = pending_mini(shell)
    pending["usage"] = client.last_usage
    return pending
