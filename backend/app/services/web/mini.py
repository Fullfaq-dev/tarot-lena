from __future__ import annotations

from datetime import date

from app.services.numerology.service import NumerologyService
from app.services.web.catalog import WebCard
from app.services.web.fragments import matrix_block, mirror_and_cut, tarot_block


def build_mini(
    card: WebCard,
    answers: list[str],
    *,
    drawn: list[dict] | None = None,
    birth: date | None = None,
    partner_birth: date | None = None,
) -> dict:
    mirror, cut = mirror_and_cut(card.id, answers)
    blocks: list[dict] = []
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
            if index == 1 and card.cards_n > 1:
                # Обрыв на полуслове — платная конкретика не в мини.
                clipped = text.rsplit(".", 1)[0]
                if "которая" not in clipped:
                    clipped = clipped.rstrip(". ") + ", которая…"
                else:
                    clipped = clipped + "…"
                text = clipped
            blocks.append({"title": position, "text": text, "image": item.get("image"), "name": item.get("name")})
            if card.cards_n == 1:
                break
        if card.id == "daily":
            cut = "Карта дня приходит каждое утро в боте — бесплатно."
        if card.id == "other":
            cut = (
                "Одна карта показывает настроение. Чтобы понять, есть ли там кто-то "
                "и насколько это серьёзно, нужен расклад из трёх карт."
            )
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
                "и держишься ровно до тех пор, пока их спасаешь. Начинается он всегда одинаково — с того, что…"
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
                "Отсюда ссоры, которые начинаются не с темы, а с…"
            ),
            "Как ты обращаешься с деньгами": (
                "Как ты обращаешься с деньгами. Канал есть, но он работает рывками: приход скачком, "
                "потом пустота. Это не «дыра», а ритм, который можно сместить."
            ),
            "Где главная утечка": (
                "Где главная утечка. Деньги уходят туда, где ты закрываешь чужую тревогу быстрее своей. "
                "По дате это повторяется…"
            ),
        }
        for title in card.open_blocks:
            blocks.append(matrix_block(title, open_copy.get(title, f"{title}. По дате этот блок уже читается.")))

    fade = card.branch != "taro" or card.cards_n > 1
    if card.id in {"daily"}:
        fade = False
        cut = "Карта дня приходит каждое утро в боте — бесплатно."
    return {
        "mirror": mirror,
        "blocks": blocks,
        "cut": cut,
        "fade": fade,
        "cta": "Открыть полный разбор" if card.price_rub else "Что дальше",
        "lead": card.lead,
        "title": card.title,
        "free": card.price_rub == 0,
    }
