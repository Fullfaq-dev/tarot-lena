"""Сайтовые карточки ситуаций. Цены не отдаём на экране 1 — только после пейвола через reading."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field


@dataclass
class QuizQuestion:
    text: str
    options: list[str]


@dataclass
class WebCard:
    id: str
    tab: str
    title: str
    icon: str
    branch: str  # taro | date | pair
    cards_n: int
    price_rub: int
    sku: str
    product_name: str
    context: str
    lead: str
    questions: list[QuizQuestion]
    positions: list[str] = field(default_factory=list)
    open_blocks: list[str] = field(default_factory=list)
    closed_blocks: list[str] = field(default_factory=list)


CARDS: dict[str, WebCard] = {}


def _add(card: WebCard) -> None:
    CARDS[card.id] = card


_add(WebCard(
    id="feels", tab="rel", title="Что он ко мне чувствует?", icon="♥",
    branch="taro", cards_n=3, price_rub=590, sku="web_love_spread",
    product_name="Расклад на отношения", context="отношения",
    lead="Вы вместе меньше года, и его молчание — то, что мучает больше всего",
    questions=[
        QuizQuestion("Как давно вы знакомы?", ["Меньше трёх месяцев", "От трёх месяцев до года", "Больше года", "Мы уже расстались"]),
        QuizQuestion("Что мучает больше всего?", ["Молчит и не объясняет", "Не зовёт в будущее", "Кажется, есть другая", "Не понимаю, чего он хочет"]),
        QuizQuestion("Чего ты хочешь сама?", ["Чтобы он определился", "Чтобы стало как раньше", "Отпустить и жить дальше", "Просто понять, что происходит"]),
    ],
    positions=["Что есть сейчас", "Что он чувствует", "К чему идёт"],
))
_add(WebCard(
    id="marry", tab="rel", title="Когда я выйду замуж?", icon="◇",
    branch="taro", cards_n=3, price_rub=590, sku="web_marry",
    product_name="Расклад на замужество", context="отношения",
    lead="Ты сейчас одна и хочешь понять срок — карты легли именно на это",
    questions=[
        QuizQuestion("Что у тебя сейчас?", ["Есть отношения, давно", "Есть, но недавно", "Сейчас одна", "Всё сложно"]),
        QuizQuestion("Что мучает больше всего?", ["Он не делает шаг", "Боюсь, что не успею", "Все вокруг уже замужем", "Не встречаю своего"]),
        QuizQuestion("Чего ты хочешь сама?", ["Понять срок", "Понять, тот ли это человек", "Узнать, что мешает", "Убедиться, что это будет"]),
    ],
    positions=["Где ты сейчас", "Что мешает", "Куда движется"],
))
_add(WebCard(
    id="return", tab="rel", title="Вернётся ли он?", icon="↺",
    branch="taro", cards_n=3, price_rub=590, sku="web_return",
    product_name="Расклад на возврат", context="расставание",
    lead="Прошло меньше трёх месяцев — для карт это ещё живая история",
    questions=[
        QuizQuestion("Как давно вы расстались?", ["Меньше месяца", "Один-три месяца", "Полгода и больше", "Больше года"]),
        QuizQuestion("Что мучает больше всего?", ["Он молчит", "Ушёл к другой", "Не понимаю причину", "Сама оттолкнула"]),
        QuizQuestion("Чего ты хочешь сама?", ["Чтобы вернулся", "Понять, стоит ли ждать", "Отпустить", "Знать правду"]),
    ],
    positions=["Что есть сейчас", "Его сторона", "Есть ли движение"],
))
_add(WebCard(
    id="other", tab="rel", title="Есть ли у него другая?", icon="◉",
    branch="taro", cards_n=1, price_rub=0, sku="web_other",
    product_name="Одна карта", context="отношения",
    lead="Ты почувствовала дистанцию — смотрим, что за ней",
    questions=[
        QuizQuestion("Что тебя насторожило?", ["Стал отдаляться", "Постоянно занят", "Прячет телефон", "Просто чувствую"]),
        QuizQuestion("Что мучает больше всего?", ["Неизвестность", "Боюсь спросить", "Он всё отрицает", "Уже находила следы"]),
        QuizQuestion("Чего ты хочешь сама?", ["Знать правду", "Понять, что делать", "Убедиться, что накручиваю", "Решиться на разговор"]),
    ],
    positions=["Состояние ситуации"],
))
_add(WebCard(
    id="alone", tab="rel", title="Почему я одна?", icon="✦",
    branch="date", cards_n=0, price_rub=990, sku="web_matrix",
    product_name="Матрица судьбы", context="отношения",
    lead="Больше трёх лет одна — в матрице это читается как повторяющийся сценарий",
    questions=[
        QuizQuestion("Как давно ты одна?", ["Меньше года", "От года до трёх", "Больше трёх лет", "Отношения были, но короткие"]),
        QuizQuestion("Что мучает больше всего?", ["Всё заканчивается одинаково", "Не встречаю своих", "Боюсь снова", "Кажется, со мной что-то не так"]),
        QuizQuestion("Чего ты хочешь сама?", ["Понять причину", "Выйти из сценария", "Убедиться, что дело не во мне", "Знать, когда встречу"]),
    ],
    open_blocks=["Какая ты", "Отношения"],
    closed_blocks=["Деньги", "Что тянется из семьи", "Главная задача", "Этот год"],
))
_add(WebCard(
    id="compat", tab="rel", title="Наша совместимость", icon="∞",
    branch="pair", cards_n=0, price_rub=890, sku="web_compat",
    product_name="Совместимость по датам", context="отношения",
    lead="Ты спросила про будущее — считаю по двум датам",
    questions=[
        QuizQuestion("Что важнее узнать?", ["Есть ли у нас будущее", "Почему мы ссоримся", "Как он меня видит", "Стоит ли ждать"]),
        QuizQuestion("Что мучает больше всего?", ["Часто ссоримся", "Не понимаем друг друга", "Разные цели", "Тянет расстаться"]),
        QuizQuestion("Чего ты хочешь сама?", ["Сохранить", "Понять, стоит ли", "Перестать ссориться", "Решиться уйти"]),
    ],
    open_blocks=["В чём вы совпадаете", "Где расходитесь"],
    closed_blocks=["Быт", "Деньги пары", "Прогноз для пары"],
))
_add(WebCard(
    id="stuck", tab="me", title="Почему всё идёт не так?", icon="◈",
    branch="date", cards_n=0, price_rub=990, sku="web_matrix",
    product_name="Матрица судьбы", context="общий прогноз",
    lead="Отношения по одному сценарию, и тянется это давно — по дате видно, откуда это взялось",
    questions=[
        QuizQuestion("Что повторяется чаще всего?", ["Отношения по одному сценарию", "Деньги не задерживаются", "Работа не складывается", "Сил ни на что нет"]),
        QuizQuestion("Как давно это тянется?", ["Меньше года", "Год-три", "Сколько себя помню", "Началось после одного события"]),
        QuizQuestion("Что хочешь понять?", ["Причину", "Как выйти из круга", "Моя ли это вина", "Когда это закончится"]),
    ],
    open_blocks=["Какая ты", "Отношения"],
    closed_blocks=["Деньги", "Что тянется из семьи", "Главная задача", "Этот год"],
))
_add(WebCard(
    id="money", tab="me", title="Куда уходят деньги?", icon="₽",
    branch="date", cards_n=0, price_rub=590, sku="web_money_channel",
    product_name="Денежный канал", context="деньги",
    lead="Зарабатываешь, но не остаётся — смотрю денежный канал",
    questions=[
        QuizQuestion("Как это ощущается сейчас?", ["Зарабатываю, но не остаётся", "Доход упёрся в потолок", "Долги", "Боюсь тратить"]),
        QuizQuestion("На чём утекает чаще?", ["Спонтанные траты", "Помогаю близким", "Постоянно что-то ломается", "Само куда-то расходится"]),
        QuizQuestion("Что для тебя «хватает»?", ["Закрыть долги", "Начать откладывать", "Не считать в магазине", "Ни от кого не зависеть"]),
    ],
    open_blocks=["Как ты обращаешься с деньгами", "Где главная утечка"],
    closed_blocks=["Что открывает канал"],
))
_add(WebCard(
    id="purpose", tab="me", title="Моё предназначение", icon="☼",
    branch="date", cards_n=0, price_rub=990, sku="web_matrix",
    product_name="Матрица судьбы", context="работа",
    lead="Ты в найме и чувствуешь, что занимаешься не своим — матрица покажет, куда разворачивает",
    questions=[
        QuizQuestion("Чем занимаешься сейчас?", ["Работаю в найме", "Своё дело", "В поиске", "В декрете"]),
        QuizQuestion("Что чувствуешь про своё дело?", ["Занимаюсь не своим", "Есть тяга, но боюсь", "Не понимаю, к чему способна", "Хочу убедиться, что иду верно"]),
        QuizQuestion("Что хочешь на выходе?", ["Конкретную сферу", "Свои сильные стороны", "Когда пора действовать", "Разрешение сменить путь"]),
    ],
    open_blocks=["Какая ты", "Сильные стороны"],
    closed_blocks=["Сфера", "Когда действовать"],
))
_add(WebCard(
    id="soon", tab="me", title="Что меня ждёт в ближайшее время?", icon="⟁",
    branch="taro", cards_n=3, price_rub=590, sku="web_forecast",
    product_name="Прогноз по картам", context="общий прогноз",
    lead="Ты выбрала деньги и смотришь на три месяца — карты легли на этот срок",
    questions=[
        QuizQuestion("Какая сфера важнее?", ["Отношения", "Деньги", "Работа", "Здоровье и силы"]),
        QuizQuestion("Как ты сейчас?", ["Жду чужого решения", "В подвешенном состоянии", "Спокойно, но тревожно", "На пороге перемен"]),
        QuizQuestion("На какой срок смотрим?", ["Месяц", "Три месяца", "Полгода"]),
    ],
    positions=["Что есть", "Что сдвинется", "Последовательность"],
))
_add(WebCard(
    id="job", tab="me", title="Стоит ли менять работу?", icon="⌁",
    branch="taro", cards_n=3, price_rub=590, sku="web_job",
    product_name="Расклад на решение", context="работа",
    lead="Ты выгорела, и держат деньги — карты показали, дело в месте или в темпе",
    questions=[
        QuizQuestion("Что сейчас не так?", ["Мало платят", "Выгорела", "Нет роста", "Конфликт с людьми"]),
        QuizQuestion("Есть куда уходить?", ["Есть конкретный вариант", "Ищу", "Хочу своё дело", "Пока просто хочу уйти"]),
        QuizQuestion("Что останавливает?", ["Деньги", "Страх ошибиться", "Жалко вложенного", "Не знаю, чего хочу"]),
    ],
    positions=["Если остаться", "Если уйти", "Что решает"],
))
_add(WebCard(
    id="daily", tab="me", title="Карта дня", icon="☾",
    branch="taro", cards_n=1, price_rub=0, sku="web_daily",
    product_name="Карта дня", context="общий прогноз",
    lead="Твоя карта на сегодня",
    questions=[
        QuizQuestion("На что смотрим сегодня?", ["Отношения", "Деньги", "Работа", "Просто день"]),
    ],
    positions=["Карта дня"],
))


def public_card(card: WebCard) -> dict:
    data = {
        "id": card.id,
        "tab": card.tab,
        "title": card.title,
        "icon": card.icon,
        "branch": card.branch,
        "cards_n": card.cards_n,
        "product_name": card.product_name,
        "questions": [{"text": q.text, "options": q.options} for q in card.questions],
        "positions": card.positions,
        "open_blocks": card.open_blocks,
        "closed_blocks": card.closed_blocks,
        "free": card.price_rub == 0,
    }
    return data


def apply_override(card: WebCard, payload: dict) -> WebCard:
    merged = deepcopy(card)
    for key in ("title", "lead", "price_rub", "product_name", "context"):
        if key in payload and payload[key] is not None:
            setattr(merged, key, payload[key])
    if "questions" in payload and isinstance(payload["questions"], list):
        merged.questions = [
            QuizQuestion(text=str(q.get("text") or ""), options=list(q.get("options") or []))
            for q in payload["questions"]
        ]
    return merged
