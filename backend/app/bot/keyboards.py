from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

MENU_TEXTS = {
    "Сделать расклад",
    "Карта дня",
    "Мой профиль",
    "Подписка и баланс",
    "История раскладов",
    "Настройки",
}

BALANCE_BUTTON_PREFIX = "Баланс:"


def balance_button_text(balance_label: str) -> str:
    return f"{BALANCE_BUTTON_PREFIX} {balance_label}"


def is_balance_button(text: str) -> bool:
    return text.startswith(BALANCE_BUTTON_PREFIX)

READING_TYPE_LABELS: dict[str, str] = {
    "love": "Любовь",
    "relationship": "Отношения",
    "money": "Деньги",
    "career": "Карьера",
    "choice": "Выбор решения",
    "past_present_future": "Прошлое / настоящее / будущее",
    "compatibility": "Совместимость",
}

READING_LABEL_TO_TYPE = {label.lower(): key for key, label in READING_TYPE_LABELS.items()}

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
    "Выбери раздел кнопкой ниже или просто напиши мне, как личному тарологу и наставнику — "
    "я отвечу в чате."
)

READINGS_MENU_TEXT = (
    "Выбери тип расклада. После выбора напиши свой вопрос обычным сообщением — "
    "я сделаю расклад и объясню карты."
)


def main_menu(balance_label: str = "0 ₽") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=balance_button_text(balance_label))],
            [KeyboardButton(text="Сделать расклад"), KeyboardButton(text="Карта дня")],
            [KeyboardButton(text="Мой профиль"), KeyboardButton(text="История раскладов")],
            [KeyboardButton(text="Настройки")],
        ],
        resize_keyboard=True,
    )


def _back_button(target: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text="← Назад", callback_data=f"nav:back:{target}")


def inline_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сделать расклад", callback_data="nav:readings"),
                InlineKeyboardButton(text="Карта дня", callback_data="nav:daily"),
            ],
            [
                InlineKeyboardButton(text="Мой профиль", callback_data="nav:profile"),
                InlineKeyboardButton(text="Пополнить баланс", callback_data="nav:billing"),
            ],
            [
                InlineKeyboardButton(text="История раскладов", callback_data="nav:history"),
                InlineKeyboardButton(text="Настройки", callback_data="nav:settings"),
            ],
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
    rows.append([_back_button("main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_reading_prompt(reading_type: str) -> InlineKeyboardMarkup:
    label = READING_TYPE_LABELS.get(reading_type, "расклад")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_back_button("readings")],
            [InlineKeyboardButton(text=f"Расклад: {label}", callback_data="nav:noop")],
        ]
    )


def inline_settings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Данные анкеты", callback_data="nav:profile_edit")],
            [InlineKeyboardButton(text="Сменить голос", callback_data="set:voice")],
            [InlineKeyboardButton(text="Сменить часовой пояс", callback_data="set:timezone")],
            [
                InlineKeyboardButton(text="Карта дня: вкл/выкл", callback_data="set:toggle:daily"),
                InlineKeyboardButton(text="Напоминания: вкл/выкл", callback_data="set:toggle:proactive"),
            ],
            [_back_button("main")],
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
                InlineKeyboardButton(text="+100 ₽", callback_data="bill:topup:100"),
                InlineKeyboardButton(text="+300 ₽", callback_data="bill:topup:300"),
                InlineKeyboardButton(text="+500 ₽", callback_data="bill:topup:500"),
            ],
            [
                InlineKeyboardButton(text="Plus 999 ₽", callback_data="bill:sub:plus"),
                InlineKeyboardButton(text="Premium 2999 ₽", callback_data="bill:sub:premium"),
            ],
            [_back_button("main")],
        ]
    )


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
    rows.append([_back_button("main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_photo_mode_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Считать ауру", callback_data="photo:mode:aura")],
            [InlineKeyboardButton(text="Считать линии на ладони", callback_data="photo:mode:palm")],
            [InlineKeyboardButton(text="Другое", callback_data="photo:mode:other")],
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
