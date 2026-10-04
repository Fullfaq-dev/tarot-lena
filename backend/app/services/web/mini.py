from __future__ import annotations

from datetime import date

from app.services.astrology.zodiac import zodiac_sign
from app.services.numerology.calculations import life_path_number
from app.services.numerology.matrix import matrix_chart
from app.services.numerology.service import NumerologyService
from app.services.tarot.cards import CARD_BACK_IMAGE, tarot_static_url
from app.services.web.catalog import WebCard
from app.services.web.fragments import matrix_block, mirror_and_cut, tarot_block
from app.services.web.mini_spec import ELEMENTS, card_accusative, pair_percent, spec_for


def _card_names(drawn: list[dict] | None) -> list[str]:
    return [str(item.get("name") or "Карта") for item in (drawn or [])]


def _cta_label(card: WebCard, drawn: list[dict] | None, answers: list[str]) -> str:
    spec = spec_for(card.id)
    names = _card_names(drawn)
    q1 = answers[0] if answers else ""
    q2 = answers[1] if len(answers) > 1 else ""
    q3 = answers[2] if len(answers) > 2 else ""
    ctx = {
        "c1": names[0] if names else "карта",
        "c2": names[1] if len(names) > 1 else "карта",
        "c3": names[2] if len(names) > 2 else (names[-1] if names else "карта"),
        "c2_acc": card_accusative(names[1] if len(names) > 1 else names[0] if names else "карта"),
        "c3_acc": card_accusative(names[2] if len(names) > 2 else names[-1] if names else "карта"),
        "q1": q1,
        "q2": q2,
        "q3": q3.lower() if q3 else q3,
    }
    try:
        return spec.cta.format(**ctx)
    except (KeyError, IndexError):
        return spec.cta


def _stats(card: WebCard, *, birth: date | None, partner_birth: date | None) -> dict | None:
    if birth is None:
        return None
    nums = NumerologyService()
    vars_ = nums.prompt_vars(name="ты", birth=birth)
    if card.branch == "pair" and partner_birth is not None:
        sign_a, emoji_a = zodiac_sign(birth)
        sign_b, emoji_b = zodiac_sign(partner_birth)
        el_a = ELEMENTS.get(sign_a, "")
        el_b = ELEMENTS.get(sign_b, "")
        life_a = int(life_path_number(birth))
        life_b = int(life_path_number(partner_birth))
        return {
            "percent": pair_percent(life_a=life_a, life_b=life_b, element_a=el_a, element_b=el_b),
            "life_paths": f"{life_a} · {life_b}",
            "signs": f"{emoji_a} {emoji_b}",
            "elements": f"{el_a} и {el_b}" if el_a and el_b else "",
            "life_path": life_a,
            "partner_life_path": life_b,
            "sign": f"{sign_a} {emoji_a}",
            "partner_sign": f"{sign_b} {emoji_b}",
            "year_arcana": str(vars_.get("year_arcana") or ""),
        }
    if card.branch in {"date", "pair"}:
        stats: dict = {
            "life_path": vars_.get("life_path"),
            "year_arcana": str(vars_.get("year_arcana") or ""),
            "sign": str(vars_.get("sign") or ""),
            "matrix": str(vars_.get("matrix") or ""),
        }
        if card.branch == "date":
            stats["chart"] = matrix_chart(birth)
        return stats
    return None


def build_mini(
    card: WebCard,
    answers: list[str],
    *,
    drawn: list[dict] | None = None,
    birth: date | None = None,
    partner_birth: date | None = None,
) -> dict:
    spec = spec_for(card.id)
    mirror, cut = mirror_and_cut(card.id, answers)
    blocks: list[dict] = []
    back = tarot_static_url(CARD_BACK_IMAGE) or "/static/tarot_cards/CardBacks.jpg"
    if card.branch == "taro":
        drawn = drawn or []
        for index, item in enumerate(drawn):
            position = card.positions[index] if index < len(card.positions) else f"Карта {index + 1}"
            text = tarot_block(
                str(item.get("name") or "Карта"),
                str(item.get("description") or "состояние ситуации"),
                position,
                card.context,
            )
            closed = spec.closed_from is not None and index >= spec.closed_from and card.price_rub > 0
            image = item.get("image")
            blocks.append(
                {
                    "title": position,
                    "text": text,
                    "image": back if closed else image,
                    "face": image,
                    "name": item.get("name"),
                    "closed": closed,
                }
            )
            if card.cards_n == 1:
                break
        if card.id == "daily":
            from app.services.web.daily_lib import daily_text

            topic = answers[0] if answers else "Просто день"
            item = drawn[0] if drawn else {}
            text = daily_text(
                name=str(item.get("name") or "Карта"),
                description=str(item.get("description") or "состояние дня"),
                topic=topic,
            )
            if blocks:
                blocks[0]["text"] = text
            cut = "Карта дня приходит каждое утро в боте - бесплатно."
    else:
        nums = NumerologyService()
        vars_ = nums.prompt_vars(
            name="ты",
            birth=birth,
            partner_bd=partner_birth.strftime("%d.%m.%Y") if partner_birth else "",
        )
        life = vars_.get("life_path") or "—"
        year = vars_.get("year_arcana") or "—"
        open_copy = {
            "Какая ты": (
                f"Какая ты. В дате читается опора на себя: число пути {life}. "
                "Со стороны это выглядит как «ей никто не нужен» — и людей это держит на расстоянии."
            ),
            "Отношения": (
                "Отношения. Сценарий повторяется не случайно: ты выбираешь тех, кому нужно быть спасённым, "
                "и держишься ровно до тех пор, пока их спасаешь."
            ),
            "Сильные стороны": (
                f"Сильные стороны. Аркан года — {year}. Это про навык, который у тебя уже есть, "
                "но ты пользуешься им в чужой роли."
            ),
            "В чём вы совпадаете": (
                "В чём вы совпадаете. По двум датам видно общий ритм: вы одинаково остро чувствуете паузы "
                "и одинаково плохо их проговариваете."
            ),
            "Где расходитесь": (
                "Где расходитесь. Темп разный: один ускоряется в стрессе, второй замирает. "
                "Отсюда ссоры, которые начинаются не с темы, а с темпа."
            ),
            "Как ты обращаешься с деньгами": (
                "Как ты обращаешься с деньгами. Канал есть, но он работает рывками: приход скачком, "
                "потом пустота. Это не «дыра», а ритм, который можно сместить."
            ),
            "Где главная утечка": (
                "Где главная утечка. Деньги уходят туда, где ты закрываешь чужую тревогу быстрее своей."
            ),
        }
        for title in card.open_blocks:
            blocks.append(matrix_block(title, open_copy.get(title, f"{title}. По дате этот блок уже читается.")))

    free = card.price_rub == 0
    library = card.id == "daily"
    return {
        "mirror": mirror,
        "blocks": blocks,
        "cut": cut,
        "fade": False,
        "cta": _cta_label(card, drawn, answers) if not library else cut,
        "lead": card.lead,
        "title": card.title,
        "free": free,
        "source": "library" if library else "shell",
        "pending": False,
        "verdict": "",
        "body": [],
        "hook": "",
        "paywall_title": "",
        "paywall_bullets": [],
        "question_example": "",
        "tg_question_example": "",
        "stats": _stats(card, birth=birth, partner_birth=partner_birth),
        "card_back": back,
    }


def mini_plain(mini: dict | None) -> str:
    data = mini or {}
    parts: list[str] = []
    verdict = str(data.get("verdict") or "").strip()
    if verdict:
        parts.append(verdict)
    for paragraph in data.get("body") or []:
        text = str(paragraph or "").strip()
        if text:
            parts.append(text)
    hook = str(data.get("hook") or "").strip()
    if hook:
        parts.append(hook)
    if parts:
        return "\n\n".join(parts)
    leftover = [str(data.get("mirror") or ""), str(data.get("lead") or ""), str(data.get("cut") or "")]
    for block in data.get("blocks") or []:
        leftover.append(str(block.get("text") or ""))
    return "\n\n".join(item.strip() for item in leftover if item and item.strip())
