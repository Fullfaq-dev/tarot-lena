"""Конфиг мини-разбора: открытые/закрытые блоки, запасные тексты, CTA."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MiniSpec:
    fallback_title: str
    fallback_bullets: tuple[str, ...]
    fallback_question: str
    cta: str
    closed_from: int | None = None
    interpret: str = ""
    paywall_title_static: str | None = None
    rule: str = ""
    max_tokens: int = 700


SPECS: dict[str, MiniSpec] = {
    "feels": MiniSpec(
        fallback_title="Узнай, к чему ведёт {c3}",
        fallback_bullets=(
            "{c3}: к чему идёт ваша история",
            "{q3}",
            "Четвёртая карта: шаг на эту неделю",
        ),
        fallback_question="А если я напишу ему первой?",
        cta="Открыть {c3_acc}",
        closed_from=2,
        interpret="Что он чувствует",
        rule=(
            "Трактуй карту на позиции «что он чувствует». "
            "«Что есть сейчас» — одной строкой. "
            "Карту на «к чему идёт» только назови в hook, не толкуй."
        ),
    ),
    "marry": MiniSpec(
        fallback_title="Узнай, куда движется твоя история",
        fallback_bullets=(
            "{c3}: куда это движется и в какой срок",
            "{q3}",
            "Четвёртая карта: что ускоряет, а что тормозит",
        ),
        fallback_question="Что ускорит это для меня?",
        cta="Открыть {c3_acc}",
        closed_from=2,
        interpret="Что мешает",
        rule=(
            "Трактуй карту на позиции «что мешает». "
            "Карту на «куда движется» только назови в hook."
        ),
    ),
    "return": MiniSpec(
        fallback_title="Узнай, есть ли движение с его стороны",
        fallback_bullets=(
            "{c3}: есть ли движение и куда",
            "{q3}",
            "Что делать на этой неделе",
        ),
        fallback_question="Стоит ли мне написать ему сейчас?",
        cta="Открыть {c3_acc}",
        closed_from=2,
        interpret="Его сторона",
        rule=(
            "Трактуй карту на позиции «его сторона». "
            "Карту на «есть ли движение» только назови в hook."
        ),
    ),
    "other": MiniSpec(
        fallback_title="Узнай, есть ли там кто-то ещё",
        fallback_bullets=(
            "{c3}: есть ли другая и насколько это серьёзно",
            "{q3}",
            "Что делать с этим знанием на этой неделе",
        ),
        fallback_question="Мне вообще спрашивать его?",
        cta="Открыть {c3_acc}",
        closed_from=2,
        interpret="Его сторона",
        rule=(
            "Трактуй карту на позиции «его сторона». "
            "Карту на «есть ли другая» только назови в hook, не толкуй."
        ),
    ),
    "alone": MiniSpec(
        fallback_title="Узнай, почему сценарий повторяется",
        fallback_bullets=("{q3}", "Что тянется из семьи", "Главная задача и этот год"),
        fallback_question="Что мне поменять в первую очередь?",
        cta="Открыть полный разбор",
        interpret="Какая ты, Отношения",
        rule="Открой блоки «какая ты» и «отношения». Деньги, семья, задача года — только назови в hook.",
    ),
    "compat": MiniSpec(
        fallback_title="Узнай, стоит ли тратить время",
        fallback_bullets=(
            "Условие, на котором держится ваше будущее",
            "Где вы будете ссориться: быт и деньги",
            "Прогноз для пары на 3 месяца",
        ),
        fallback_question="А если мы съедемся?",
        cta="Открыть разбор пары",
        paywall_title_static="Узнай, стоит ли тратить время",
        interpret="В чём вы совпадаете, Где расходитесь",
        rule=(
            "Открой совпадения и расхождения. Быт, деньги пары и прогноз — в hook. "
            "Процент в тексте не повторяй. paywall_title не пиши."
        ),
    ),
    "stuck": MiniSpec(
        fallback_title="Узнай, откуда это тянется",
        fallback_bullets=("{q3}", "Что тянется из семьи", "Главная задача и этот год"),
        fallback_question="С чего начать, чтобы выйти из круга?",
        cta="Открыть полный разбор",
        interpret="Какая ты, Отношения",
        rule="Открой «какая ты» и «отношения». Семья, задача и этот год — в hook.",
    ),
    "money": MiniSpec(
        fallback_title="Узнай, что открывает твой денежный канал",
        fallback_bullets=(
            "{q3}",
            "Где утечка повторяется и как её закрыть",
            "Что открывает канал",
        ),
        fallback_question="Почему я зарабатываю, но деньги не остаются?",
        cta="Открыть денежный канал",
        interpret="Как ты обращаешься с деньгами",
        rule=(
            "Открой, как она обращается с деньгами, и начало «где главная утечка». "
            "Конец утечки и «что открывает канал» — в hook."
        ),
    ),
    "purpose": MiniSpec(
        fallback_title="Узнай свою сферу и месяц для первого шага",
        fallback_bullets=(
            "{q3}",
            "2–3 сферы, где работает твоё число пути",
            "Месяцы, когда начинать, и когда подождать",
        ),
        fallback_question="А если совмещать с работой?",
        cta="Открыть сферу и сроки",
        interpret="Какая ты, Сильные стороны",
        rule=(
            "Открой «какая ты» и сильные стороны. Используй число пути и аркан года. "
            "Сферу и месяцы только назови в hook, не раскрывай."
        ),
    ),
    "soon": MiniSpec(
        fallback_title="Узнай, что сдвинется за {q3}",
        fallback_bullets=(
            "{c2}: что именно сдвинется в сфере «{q1}»",
            "{c3}: в какой последовательности",
            "Карта-совет",
        ),
        fallback_question="В какой месяц ждать перемен?",
        cta="Открыть {c2_acc}",
        closed_from=1,
        interpret="Что есть",
        rule=(
            "Трактуй карту «что есть». «Что сдвинется» и «последовательность» только назови в hook."
        ),
    ),
    "job": MiniSpec(
        fallback_title="Узнай, что будет, если уйти",
        fallback_bullets=(
            "{c2}: что будет, если уйти",
            "{c3}: что решает",
            "Карта-совет про «{q2}»",
        ),
        fallback_question="А если уйти в своё дело?",
        cta="Открыть {c2_acc}",
        closed_from=1,
        interpret="Если остаться",
        rule="Трактуй «если остаться». «Если уйти» и «что решает» только назови в hook.",
    ),
    "daily": MiniSpec(
        fallback_title="",
        fallback_bullets=(),
        fallback_question="",
        cta="Карта дня приходит каждое утро в боте — бесплатно.",
        rule="Без нейросети.",
    ),
}


LIFE_PATH_WORD = {
    1: "единица",
    2: "двойка",
    3: "тройка",
    4: "четвёрка",
    5: "пятёрка",
    6: "шестёрка",
    7: "семёрка",
    8: "восьмёрка",
    9: "девятка",
    11: "одиннадцать",
    22: "двадцать два",
    33: "тридцать три",
}

MAJOR_ACCUSATIVE = {
    "Шут": "Шута",
    "Маг": "Мага",
    "Жрица": "Жрицу",
    "Императрица": "Императрицу",
    "Император": "Императора",
    "Иерофант": "Иерофанта",
    "Влюбленные": "Влюблённых",
    "Влюблённые": "Влюблённых",
    "Колесница": "Колесницу",
    "Сила": "Силу",
    "Отшельник": "Отшельника",
    "Колесо Фортуны": "Колесо Фортуны",
    "Справедливость": "Справедливость",
    "Повешенный": "Повешенного",
    "Смерть": "Смерть",
    "Умеренность": "Умеренность",
    "Дьявол": "Дьявола",
    "Башня": "Башню",
    "Звезда": "Звезду",
    "Луна": "Луну",
    "Солнце": "Солнце",
    "Суд": "Суд",
    "Мир": "Мир",
}

_RANK_ACCUSATIVE = {
    "Туз": "Туза",
    "Двойка": "Двойку",
    "Тройка": "Тройку",
    "Четвёрка": "Четвёрку",
    "Пятёрка": "Пятёрку",
    "Шестёрка": "Шестёрку",
    "Семёрка": "Семёрку",
    "Восьмёрка": "Восьмёрку",
    "Девятка": "Девятку",
    "Десятка": "Десятку",
    "Паж": "Пажа",
    "Рыцарь": "Рыцаря",
    "Королева": "Королеву",
    "Король": "Короля",
}

ELEMENTS = {
    "Овен": "Огонь",
    "Лев": "Огонь",
    "Стрелец": "Огонь",
    "Телец": "Земля",
    "Дева": "Земля",
    "Козерог": "Земля",
    "Близнецы": "Воздух",
    "Весы": "Воздух",
    "Водолей": "Воздух",
    "Рак": "Вода",
    "Скорпион": "Вода",
    "Рыбы": "Вода",
}

_CRAWLER_UA = (
    "bot",
    "crawler",
    "spider",
    "slurp",
    "bingpreview",
    "facebookexternalhit",
    "whatsapp",
    "telegrambot",
    "embedly",
    "quora link preview",
    "outbrain",
    "pinterest",
    "slackbot",
    "vkshare",
    "w3c_validator",
)


def spec_for(card_id: str) -> MiniSpec:
    return SPECS.get(card_id) or MiniSpec(
        fallback_title="Узнай полный разбор",
        fallback_bullets=("Закрытые блоки расклада", "Ответ на твой вопрос", "Шаг на эту неделю"),
        fallback_question="Что мне делать дальше?",
        cta="Открыть полный разбор",
    )


def card_accusative(name: str) -> str:
    if name in MAJOR_ACCUSATIVE:
        return MAJOR_ACCUSATIVE[name]
    for rank, acc in _RANK_ACCUSATIVE.items():
        prefix = f"{rank} "
        if name.startswith(prefix):
            return acc + name[len(rank) :]
    return name


def life_path_word(value: object) -> str:
    try:
        number = int(str(value))
    except (TypeError, ValueError):
        return "число пути"
    return LIFE_PATH_WORD.get(number, str(number))


def is_crawler(user_agent: str | None) -> bool:
    blob = (user_agent or "").lower()
    if not blob:
        return False
    return any(token in blob for token in _CRAWLER_UA)


def pair_percent(*, life_a: int, life_b: int, element_a: str, element_b: str) -> int:
    score = 74 - min(abs(life_a - life_b), 8) * 4
    if element_a == element_b:
        score += 8
    elif {element_a, element_b} in ({"Огонь", "Воздух"}, {"Земля", "Вода"}):
        score += 3
    else:
        score -= 6
    return max(38, min(86, score))


GIFT_TITLE = "В подарок: 3 уточняющих вопроса к твоему разбору"

PAYWALL_COPY = {
    "taro": {
        "algorithm": "Карты раскладывает алгоритм, без ручных ошибок. Ответ через минуту",
        "price_caption": "индивидуальный разбор + 3 вопроса",
    },
    "date": {
        "algorithm": "Числа считает алгоритм, без ручных ошибок. Ответ через минуту",
        "price_caption": "индивидуальный расчёт + 3 вопроса",
    },
    "pair": {
        "algorithm": "Числа считает алгоритм, без ручных ошибок. Ответ через минуту",
        "price_caption": "индивидуальный расчёт + 3 вопроса",
    },
}


@dataclass(frozen=True)
class PayOffer:
    subtitle: str
    cta: str
    eyebrow: str


_TARO_OFFER = PayOffer(
    subtitle="Расклад откроется целиком, а потом ты задаёшь Лее вопросы по нему.",
    cta="Открыть расклад за {price} ₽",
    eyebrow="Полный расклад",
)
_MATRIX_OFFER = PayOffer(
    subtitle="Матрица уже посчитана. Откроешь трактовку и спросишь Лею про работу и деньги.",
    cta="Открыть матрицу за {price} ₽",
    eyebrow="Матрица судьбы",
)

OFFERS: dict[str, PayOffer] = {
    "feels": _TARO_OFFER,
    "marry": _TARO_OFFER,
    "return": _TARO_OFFER,
    "other": _TARO_OFFER,
    "soon": _TARO_OFFER,
    "job": _TARO_OFFER,
    "money": PayOffer(
        subtitle="Канал уже читается. Откроешь, где утечка и что его открывает.",
        cta="Открыть канал за {price} ₽",
        eyebrow="Денежный канал",
    ),
    "compat": PayOffer(
        subtitle="Откроешь разбор пары и задашь Лее вопросы про вас двоих.",
        cta="Открыть совместимость за {price} ₽",
        eyebrow="Полная совместимость",
    ),
    "alone": _MATRIX_OFFER,
    "stuck": _MATRIX_OFFER,
    "purpose": _MATRIX_OFFER,
}

_DATE_IDS = {"money", "alone", "stuck", "purpose"}


def pay_offer(card_id: str) -> PayOffer:
    return OFFERS.get(card_id) or _TARO_OFFER


def paywall_copy(branch: str) -> dict[str, str]:
    return PAYWALL_COPY.get(branch) or PAYWALL_COPY["taro"]


def offer_branch(card_id: str, branch: str = "") -> str:
    if branch in PAYWALL_COPY:
        return branch
    if card_id == "compat":
        return "pair"
    if card_id in _DATE_IDS:
        return "date"
    return "taro"


def offer_payload(
    card_id: str,
    *,
    price_rub: int,
    show_strike: bool,
    question_price: int,
    mini: dict | None = None,
    branch: str = "",
) -> dict:
    offer = pay_offer(card_id)
    spec = spec_for(card_id)
    mini = mini or {}
    copy = paywall_copy(offer_branch(card_id, branch))
    strike = price_rub + 3 * question_price if show_strike and price_rub > 0 else 0
    title = str(mini.get("paywall_title") or spec.paywall_title_static or spec.fallback_title or offer.eyebrow)
    question_example = str(mini.get("question_example") or "").strip() or spec.fallback_question
    return {
        "eyebrow": offer.eyebrow,
        "title": title,
        "subtitle": offer.subtitle,
        "cta": offer.cta.format(price=price_rub),
        "gift": GIFT_TITLE,
        "algorithm": copy["algorithm"],
        "price_caption": copy["price_caption"],
        "question_example": question_example,
        "price_rub": price_rub,
        "strike_rub": strike,
        "show_strike": bool(show_strike and strike > price_rub),
        "question_price": question_price,
        "fine": "СБП или карта · без подписки · откроется сразу здесь",
    }
