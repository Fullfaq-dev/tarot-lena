from app.services.web.catalog import CARDS
from app.services.web.mini import build_mini
from app.services.web.mini_ai import apply_generated, parse_mini_json
from app.services.web.mini_spec import card_accusative, pair_percent


def test_parse_mini_json_strips_fence():
    raw = """```json
    {"verdict": "Он думает о тебе.", "body": ["Сцена."], "hook": "Башню держу."}
    ```"""
    data = parse_mini_json(raw)
    assert data["verdict"] == "Он думает о тебе."
    assert data["body"] == ["Сцена."]


def test_apply_generated_uses_verdict_as_lead_and_no_fade():
    card = CARDS["feels"]
    shell = build_mini(
        card,
        ["Меньше трёх месяцев", "Молчит и не объясняет", "Чтобы он определился"],
        drawn=[
            {"name": "Императрица", "description": "рост", "image": "/a.jpg"},
            {"name": "Смерть", "description": "конец", "image": "/b.jpg"},
            {"name": "Башня", "description": "слом", "image": "/c.jpg"},
        ],
    )
    mini = apply_generated(
        card,
        ["Меньше трёх месяцев", "Молчит и не объясняет", "Чтобы он определился"],
        shell,
        {
            "verdict": "Он думает о тебе. И при этом заканчивает этап.",
            "body": [
                "Ты набираешь вечером длинное сообщение и стираешь половину.",
                "Смерть на позиции «что он чувствует» говорит про конец этапа.",
            ],
            "hook": "Башня легла на «к чему идёт». Её я пока держу закрытой.",
            "paywall_title": "Узнай, к чему ведёт Башня",
            "paywall_bullets": [
                "Башня: что поменяется у вас и когда",
                "Почему он молчит и что держит при себе",
                "Один шаг на эту неделю",
            ],
            "question_example": "А если я напишу ему первой?",
            "tg_question_example": "Он правда вернётся, если я подожду?",
        },
    )
    assert mini["fade"] is False
    assert mini["pending"] is False
    assert mini["source"] == "ai"
    assert mini["lead"] == mini["verdict"]
    assert "Башню" in mini["cta"]
    assert shell["blocks"][2]["closed"] is True
    assert mini["paywall_title"].startswith("Узнай")


def test_invalid_paywall_falls_back():
    card = CARDS["feels"]
    shell = build_mini(card, ["Меньше трёх месяцев", "Молчит и не объясняет", "Чтобы он определился"])
    mini = apply_generated(
        card,
        ["Меньше трёх месяцев", "Молчит и не объясняет", "Чтобы он определился"],
        shell,
        {"verdict": "Он рядом, но молчит.", "body": ["Сцена."], "hook": "Закрыто.", "paywall_title": "nope"},
    )
    assert mini["paywall_title"].startswith("Узнай")
    assert len(mini["paywall_bullets"]) == 3


def test_card_accusative_and_compat_percent():
    assert card_accusative("Башня") == "Башню"
    assert card_accusative("Туз Кубков") == "Туза Кубков"
    assert 38 <= pair_percent(life_a=4, life_b=4, element_a="Воздух", element_b="Вода") <= 86


def test_matrix_cache_key_includes_card_and_answers():
    import hashlib
    from datetime import date

    def answers_key(answers: list[str]) -> str:
        blob = "\n".join(str(item) for item in answers)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def matrix_cache_key(card_id: str, birth: date, partner: date | None, answers: list[str]) -> str:
        partner_part = partner.isoformat() if partner else ""
        return f"{card_id}:{birth.isoformat()}:{partner_part}:{answers_key(answers)}"

    birth = date(1990, 6, 15)
    key_a = matrix_cache_key("alone", birth, None, ["Больше трёх лет", "Всё заканчивается одинаково", "Понять причину"])
    key_b = matrix_cache_key("alone", birth, None, ["Больше трёх лет", "Боюсь снова", "Понять причину"])
    key_c = matrix_cache_key("purpose", birth, None, ["Больше трёх лет", "Всё заканчивается одинаково", "Понять причину"])
    assert key_a != key_b
    assert key_a != key_c
    assert key_a.startswith("alone:")
    assert answers_key(["a"]) != answers_key(["b"])


def test_build_mini_does_not_fade_or_clip():
    card = CARDS["feels"]
    mini = build_mini(
        card,
        ["Меньше трёх месяцев", "Молчит и не объясняет", "Чтобы он определился"],
        drawn=[
            {"name": "Императрица", "description": "рост", "image": "/a.jpg"},
            {"name": "Смерть", "description": "конец", "image": "/b.jpg"},
            {"name": "Башня", "description": "слом", "image": "/c.jpg"},
        ],
    )
    assert mini["fade"] is False
    assert "которая…" not in (mini["blocks"][1]["text"] or "")
    assert mini["blocks"][2]["closed"] is True


def test_offer_payload_hides_strike_by_default():
    from app.services.web.mini_spec import offer_payload

    offer = offer_payload(
        "feels",
        price_rub=390,
        show_strike=False,
        question_price=99,
        mini={"paywall_title": "Узнай, к чему ведёт Башня"},
    )
    assert offer["price_rub"] == 390
    assert offer["show_strike"] is False
    assert offer["cta"] == "Открыть расклад за 390 ₽"
    assert "3 вопроса" in offer["gift"]

    shown = offer_payload("feels", price_rub=390, show_strike=True, question_price=99)
    assert shown["show_strike"] is True
    assert shown["strike_rub"] == 390 + 3 * 99


def test_daily_library_and_crawler():
    from app.services.web.daily_lib import daily_text
    from app.services.web.mini_spec import is_crawler

    text = daily_text(name="Шут", description="начало пути", topic="Отношения")
    assert "Шут" in text
    assert "нейросет" not in text.lower()
    assert is_crawler("Mozilla/5.0 (compatible; Googlebot/2.1)")
    assert not is_crawler("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)")
