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
    from app.services.web.mini_spec import GIFT_TITLE, offer_payload

    offer = offer_payload(
        "feels",
        price_rub=390,
        show_strike=False,
        question_price=99,
        mini={"paywall_title": "Узнай, к чему ведёт Башня"},
        branch="taro",
    )
    assert offer["price_rub"] == 390
    assert offer["show_strike"] is False
    assert offer["strike_rub"] == 0
    assert offer["cta"] == "Открыть расклад за 390 ₽"
    assert offer["gift"] == GIFT_TITLE
    assert offer["algorithm"].startswith("Карты раскладывает")
    assert "compare" not in offer
    blob = " ".join(str(v) for v in offer.values())
    assert "Консультация" not in blob
    assert "99 ₽" not in blob

    shown = offer_payload("feels", price_rub=390, show_strike=True, question_price=99, branch="taro")
    assert shown["show_strike"] is True
    assert shown["strike_rub"] == 690
    assert shown["price_caption"] == "индивидуальный разбор"
    assert "99" not in shown["price_caption"]


def test_paywall_copy_and_strike_table():
    from app.services.web.catalog import FALLBACK_QUESTIONS, public_card
    from app.services.web.mini_spec import GIFT_TITLE, offer_payload

    table = {
        "feels": ("taro", 390, 690),
        "marry": ("taro", 390, 690),
        "return": ("taro", 390, 690),
        "soon": ("taro", 390, 690),
        "job": ("taro", 390, 690),
        "money": ("date", 490, 890),
        "alone": ("date", 490, 890),
        "stuck": ("date", 490, 890),
        "purpose": ("date", 490, 890),
        "compat": ("pair", 490, 890),
    }
    for card_id, (branch, price, strike) in table.items():
        card = CARDS[card_id]
        assert card.price_rub == price
        assert card.fallback_question == FALLBACK_QUESTIONS[card_id]
        assert public_card(card)["fallback_question"] == card.fallback_question
        hidden = offer_payload(card_id, price_rub=price, show_strike=False, question_price=99, branch=branch)
        shown = offer_payload(card_id, price_rub=price, show_strike=True, question_price=99, branch=branch)
        assert hidden["gift"] == shown["gift"] == GIFT_TITLE
        assert hidden["show_strike"] is False
        assert hidden["strike_rub"] == 0
        assert shown["show_strike"] is True
        assert shown["strike_rub"] == strike
        if branch == "taro":
            assert hidden["algorithm"].startswith("Карты раскладывает")
            assert shown["price_caption"] == "индивидуальный разбор"
        else:
            assert hidden["algorithm"].startswith("Числа считает")
            assert shown["price_caption"] == "индивидуальный расчёт"

    # Если цену в админке поднять до зачёркнутой или выше, зачёркнутая цена не показывается.
    override = offer_payload("feels", price_rub=900, show_strike=True, question_price=99, branch="taro")
    assert override["show_strike"] is False
    money = offer_payload("money", price_rub=590, show_strike=False, question_price=99, mini={})
    assert money["question_example"] == FALLBACK_QUESTIONS["money"]


def test_daily_library_and_crawler():
    from app.services.web.daily_lib import daily_text
    from app.services.web.mini_spec import is_crawler

    text = daily_text(name="Шут", description="начало пути", topic="Отношения")
    assert "Шут" in text
    assert "нейросет" not in text.lower()
    assert is_crawler("Mozilla/5.0 (compatible; Googlebot/2.1)")
    assert not is_crawler("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)")


def test_other_card_is_paid_three_spread():
    card = CARDS["other"]
    assert card.cards_n == 3
    assert card.price_rub > 0
    from app.services.web.mini_spec import spec_for

    spec = spec_for("other")
    assert spec.closed_from == 2
    mini = build_mini(
        card,
        ["Стал отдаляться", "Неизвестность", "Знать правду"],
        drawn=[
            {"name": "Луна", "description": "туман", "image": "/a.jpg"},
            {"name": "Дьявол", "description": "связь", "image": "/b.jpg"},
            {"name": "Башня", "description": "правда", "image": "/c.jpg"},
        ],
    )
    assert mini["free"] is False
    assert mini["blocks"][2]["closed"] is True


def test_pay_return_uses_paid_reading_token_not_cabinet():
    from app.services.web.pay_return import pick_return_token, reading_return_path

    paid = "reading-paid-abc"
    other = "reading-other-xyz"
    assert pick_return_token(shp_token=paid, payment_token=other, cookie_token=other) == paid
    assert pick_return_token(shp_token="", payment_token=paid, cookie_token=other) == paid
    assert pick_return_token(shp_token="", payment_token="", cookie_token=paid) == paid
    assert pick_return_token() == ""
    assert reading_return_path(paid) == "/r/reading-paid-abc?paid=1"


def test_robokassa_lk_return_never_asks_login():
    from app.services.web.pay_return import bypass_login_return_path, is_robokassa_return_path

    token = "UR2ZbJiJkAqDLDcrk22QyQ"
    assert is_robokassa_return_path("/lk")
    assert bypass_login_return_path(path="/lk", shp_token=token) == f"/r/{token}?paid=1"
    assert bypass_login_return_path(path="/payment/success", shp_token=token) == f"/r/{token}?paid=1"
    assert bypass_login_return_path(path="/lk", shp_token="") == ""


def test_web_catalog_live_prices():
    from app.services.web.catalog import CARDS, TEST_WEB_PRICE_RUB

    assert TEST_WEB_PRICE_RUB is None
    assert CARDS["daily"].price_rub == 0
    # Таро — 390 ₽
    for card_id in ("feels", "marry", "return", "other", "soon", "job"):
        assert CARDS[card_id].price_rub == 390, card_id
    # Расчёты по датам и совместимость — 490 ₽
    for card_id in ("money", "compat", "alone", "stuck", "purpose"):
        assert CARDS[card_id].price_rub == 490, card_id


def test_paid_markdown_becomes_headings_and_italic():
    from app.bot.formatting import leia_markdown_to_web_html

    html = leia_markdown_to_web_html(
        "# # # Твоё предназначение\n\nТы сильнее там, где можешь влиять на то, *как устроена работа*.\n\n### Сфера\n\nКоординация проектов."
    )
    assert "<h3>" in html
    assert "Твоё предназначение" in html
    assert "###" not in html
    assert "# # #" not in html
    assert "<i>" in html
    assert "как устроена работа" in html


def test_second_chat_turn_sends_assistant_as_output_text():
    from app.services.ai.kie_client import _messages_to_responses_input, _normalize_messages

    instructions, items = _messages_to_responses_input(
        _normalize_messages(
            [
                {"role": "system", "content": [{"type": "text", "text": "Ты Лея."}]},
                {"role": "user", "content": [{"type": "text", "text": "Первый вопрос"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "Ответ Леи"}]},
                {"role": "user", "content": [{"type": "text", "text": "Второй вопрос"}]},
            ]
        )
    )
    assert "Ты Лея." in instructions
    assert [item["role"] for item in items] == ["user", "assistant", "user"]
    assert items[0]["content"][0]["type"] == "input_text"
    assert items[1]["content"][0]["type"] == "output_text"
    assert items[1]["content"][0]["text"] == "Ответ Леи"
    assert items[2]["content"][0]["type"] == "input_text"
    assert items[2]["content"][0]["text"] == "Второй вопрос"


def test_three_pay_options():
    from app.services.web.mini_spec import OPTION_BADGE, offer_payload

    taro = offer_payload("feels", price_rub=390, show_strike=True, question_price=99, branch="taro")
    opts = {o["id"]: o for o in taro["options"]}
    assert [o["id"] for o in taro["options"]] == ["base", "plus3", "pass30"]
    assert (opts["base"]["price_rub"], opts["base"]["strike_rub"]) == (390, 690)
    assert (opts["plus3"]["price_rub"], opts["plus3"]["strike_rub"]) == (590, 990)
    assert (opts["pass30"]["price_rub"], opts["pass30"]["strike_rub"]) == (990, 1690)
    assert opts["plus3"]["featured"] is True and opts["plus3"]["badge"] == OPTION_BADGE
    assert taro["guarantee"] == "Не откликнулось — верну деньги, без вопросов"
    assert taro["cta"] == "Открыть расклад за 390 ₽"

    calc = offer_payload("compat", price_rub=490, show_strike=True, question_price=99, branch="pair")
    copts = {o["id"]: o for o in calc["options"]}
    assert (copts["base"]["price_rub"], copts["base"]["strike_rub"]) == (490, 890)
    assert (copts["plus3"]["price_rub"], copts["plus3"]["strike_rub"]) == (690, 1190)
    assert "расчёт" in copts["base"]["caption"]

    # скидка в пределах 40–45 %
    for o in taro["options"] + calc["options"]:
        discount = 1 - o["price_rub"] / o["strike_rub"]
        assert 0.39 <= discount <= 0.46, (o["id"], discount)

    hidden = offer_payload("feels", price_rub=390, show_strike=False, question_price=99, branch="taro")
    assert all(o["strike_rub"] == 0 for o in hidden["options"])
    assert offer_payload("daily", price_rub=0, show_strike=True, question_price=99, branch="taro")["options"] == []


def test_question_budget_by_tariff():
    from types import SimpleNamespace

    from app.services.web.service import UNLIMITED_QUESTIONS, _question_budget

    def budget(payload):
        return _question_budget(SimpleNamespace(input_payload=payload))

    assert budget({"paid_tariff": "base"}) == 0
    assert budget({"paid_tariff": "plus3"}) == 3
    assert budget({"paid_tariff": "pass30"}) == UNLIMITED_QUESTIONS
    assert budget({"paid_tariff": "unlimited"}) == UNLIMITED_QUESTIONS
    assert budget({}) == 3  # оплаченные до трёх вариантов — как раньше
    assert budget({"paid_tariff": "base", "question_credits": 5}) == 5


def test_unlimited_option_after_first_purchase():
    from app.services.web.mini_spec import offer_payload

    first = offer_payload("feels", price_rub=390, show_strike=True, question_price=99, branch="taro")
    assert first["options"][2]["id"] == "pass30"
    assert "без подписки" in first["fine"]

    again = offer_payload(
        "feels", price_rub=390, show_strike=True, question_price=99, branch="taro", returning=True, sub_price=590
    )
    sub = again["options"][2]
    assert [o["id"] for o in again["options"]] == ["base", "plus3", "unlimited"]
    assert (sub["price_rub"], sub["strike_rub"]) == (590, 990)
    assert sub["title"].startswith("VIP-доступ на 30 дней")
    assert "без автопродления" in sub["caption"]
