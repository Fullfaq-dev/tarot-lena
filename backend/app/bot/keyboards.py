from urllib.parse import quote

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_READINGS = "🔮 Сделать расклад"
BTN_DAILY = "🌅 Карта дня"
BTN_PROFILE = "👤 Мой профиль"
BTN_HISTORY = "📜 История раскладов"
BTN_SETTINGS = "⚙️ Настройки"

# Старые подписи оставляем рабочими — у части пользователей в чате осталась старая клавиатура.
MENU_ACTIONS: dict[str, str] = {
    BTN_READINGS: "readings",
    BTN_DAILY: "daily",
    BTN_PROFILE: "profile",
    BTN_HISTORY: "history",
    BTN_SETTINGS: "settings",
    "Сделать расклад": "readings",
    "Карта дня": "daily",
    "Мой профиль": "profile",
    "История раскладов": "history",
    "Настройки": "settings",
    "Подписка и баланс": "billing",
}

MENU_TEXTS = set(MENU_ACTIONS.keys())

BALANCE_BUTTON_PREFIX = "💰 Баланс:"
_OLD_BALANCE_PREFIX = "Баланс:"


def balance_button_text(balance_label: str) -> str:
    return f"{BALANCE_BUTTON_PREFIX} {balance_label}"


def is_balance_button(text: str) -> bool:
    return text.startswith(BALANCE_BUTTON_PREFIX) or text.startswith(_OLD_BALANCE_PREFIX)


READING_TYPE_LABELS: dict[str, str] = {
    "love": "💞 Любовь",
    "relationship": "💑 Отношения",
    "money": "💸 Деньги",
    "career": "🚀 Карьера",
    "choice": "🤔 Выбор решения",
    "past_present_future": "⏳ Прошлое / настоящее / будущее",
    "compatibility": "✨ Совместимость",
}


def _plain_label(label: str) -> str:
    return label.split(" ", 1)[1] if " " in label and not label[0].isalnum() else label


READING_LABEL_TO_TYPE = {
    **{label.lower(): key for key, label in READING_TYPE_LABELS.items()},
    **{_plain_label(label).lower(): key for key, label in READING_TYPE_LABELS.items()},
}

ONBOARDING_CHOICES: dict[str, list[str]] = {
    "gender": ["мужской", "женский", "не указывать"],
    "relationship_status": [
        "свободен/свободна",
        "в отношениях",
        "женат/замужем",
        "в разводе",
        "сложно",
    ],
    "has_children": ["да", "нет"],
    "main_concern": ["отношения", "деньги", "карьера", "здоровье", "саморазвитие", "другое"],
    "belief_system": ["таро", "астрология", "нумерология", "энергия", "тонкие материи", "всё сразу"],
}

MAIN_MENU_TEXT = (
    "✨ Что делаем дальше?\n\n"
    "Выбери раздел кнопкой ниже — или просто напиши мне сообщение, "
    "как личному тарологу. Я помню твою историю и отвечу с учётом контекста.\n\n"
    "📸 Можешь прислать фото — я считаю ауру или линии ладони."
)

READINGS_MENU_TEXT = (
    "🔮 Выбери тему расклада.\n\n"
    "После выбора напиши свой вопрос обычным сообщением — "
    "я вытяну карты и объясню, что они значат именно для тебя."
)


def main_menu(balance_label: str = "0 ₽") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=balance_button_text(balance_label))],
            [KeyboardButton(text=BTN_READINGS), KeyboardButton(text=BTN_DAILY)],
            [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_HISTORY)],
            [KeyboardButton(text=BTN_SETTINGS)],
        ],
        resize_keyboard=True,
    )


def _home_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🏠 На главную", callback_data="nav:back:main")


def _back_button(target: str) -> InlineKeyboardButton:
    if target == "main":
        return _home_button()
    return InlineKeyboardButton(text="← Назад", callback_data=f"nav:back:{target}")


def inline_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔮 Сделать расклад", callback_data="nav:readings"),
                InlineKeyboardButton(text="🌅 Карта дня", callback_data="nav:daily"),
            ],
            [
                InlineKeyboardButton(text="👤 Мой профиль", callback_data="nav:profile"),
                InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="nav:billing"),
            ],
            [
                InlineKeyboardButton(text="📜 История раскладов", callback_data="nav:history"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="nav:settings"),
            ],
            [InlineKeyboardButton(text="🤝 Пригласить подругу · 40%", callback_data="nav:referrals")],
        ]
    )


def inline_readings_menu() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for key, label in READING_TYPE_LABELS.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"nav:reading:{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_home_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_reading_prompt(reading_type: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_back_button("readings")],
            [_home_button()],
        ]
    )


def inline_settings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Данные анкеты", callback_data="nav:profile_edit")],
            [InlineKeyboardButton(text="🎙 Сменить голос", callback_data="set:voice")],
            [InlineKeyboardButton(text="🕐 Сменить часовой пояс", callback_data="set:timezone")],
            [
                InlineKeyboardButton(text="🌅 Карта дня: вкл/выкл", callback_data="set:toggle:daily"),
                InlineKeyboardButton(text="🔔 Напоминания: вкл/выкл", callback_data="set:toggle:proactive"),
            ],
            [_home_button()],
        ]
    )


def _profile_button_text(label: str, value: str) -> str:
    text = f"{label}: {value}"
    return text if len(text) <= 60 else f"{text[:57]}…"


def inline_profile_edit_menu(rows: list[tuple[str, str, str]]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    line: list[InlineKeyboardButton] = []
    for field_key, label, value in rows:
        line.append(
            InlineKeyboardButton(
                text=_profile_button_text(label, value),
                callback_data=f"set:prof:{field_key}",
            )
        )
        if len(line) == 2:
            buttons.append(line)
            line = []
    if line:
        buttons.append(line)
    buttons.append([InlineKeyboardButton(text="← Назад в настройки", callback_data="nav:settings")])
    buttons.append([_home_button()])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def profile_field_keyboard(field_key: str) -> InlineKeyboardMarkup | None:
    options = ONBOARDING_CHOICES.get(field_key)
    if not options:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="← Назад", callback_data="nav:profile_edit")],
            ]
        )

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for option in options:
        row.append(
            InlineKeyboardButton(text=option, callback_data=f"prof:pick:{field_key}:{option}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="nav:profile_edit")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_billing_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 +100 ₽", callback_data="bill:topup:100"),
                InlineKeyboardButton(text="💳 +300 ₽", callback_data="bill:topup:300"),
                InlineKeyboardButton(text="💳 +500 ₽", callback_data="bill:topup:500"),
            ],
            [
                InlineKeyboardButton(text="✨ Plus · 999 ₽/мес", callback_data="bill:sub:plus"),
                InlineKeyboardButton(text="👑 Premium · 2999 ₽/мес", callback_data="bill:sub:premium"),
            ],
            [InlineKeyboardButton(text="🤝 Реферальная программа", callback_data="nav:referrals")],
            [_home_button()],
        ]
    )


def inline_referral_menu(*, share_link: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🔗 Моя ссылка-приглашение", callback_data="ref:share")],
    ]
    if share_link:
        share_text = "🔮 Попробуй AI-таролога — мне очень нравится!"
        share_url = (
            "https://t.me/share/url?"
            f"url={quote(share_link)}&text={quote(share_text)}"
        )
        rows.append(
            [InlineKeyboardButton(text="📤 Отправить подруге", url=share_url)]
        )
    rows.append([InlineKeyboardButton(text="💸 Вывести средства", callback_data="ref:withdraw")])
    rows.append([_home_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_withdraw_wallet_menu(saved_wallet: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if saved_wallet:
        short = f"{saved_wallet[:6]}…{saved_wallet[-4:]}"
        rows.append(
            [InlineKeyboardButton(text=f"✅ На сохранённый ({short})", callback_data="ref:wallet_saved")]
        )
    rows.append([InlineKeyboardButton(text="✏️ Указать другой кошелёк", callback_data="ref:wallet_new")])
    rows.append([_home_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_history_menu(readings: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for index, reading in enumerate(readings, start=1):
        label = READING_TYPE_LABELS.get(reading.reading_type, reading.reading_type)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{index}. {label}",
                    callback_data=f"hist:open:{reading.id}",
                )
            ]
        )
    rows.append([_home_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_photo_mode_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌈 Аура — 100 ₽", callback_data="photo:mode:aura")],
            [InlineKeyboardButton(text="🖐 Ладонь — 100 ₽", callback_data="photo:mode:palm")],
            [InlineKeyboardButton(text="💬 Свой вопрос по фото", callback_data="photo:mode:other")],
            [_home_button()],
        ]
    )


def onboarding_keyboard(step_key: str) -> InlineKeyboardMarkup | None:
    options = ONBOARDING_CHOICES.get(step_key)
    if not options:
        return None

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for option in options:
        row.append(InlineKeyboardButton(text=option, callback_data=f"onb:pick:{step_key}:{option}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="← Назад", callback_data="onb:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
