from urllib.parse import quote

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.bot.content import LEGAL_URL, support_url
from app.bot.i18n import (
    btn_daily,
    btn_energy,
    btn_history,
    btn_info,
    btn_language,
    btn_readings,
    btn_settings,
    btn_support,
    btn_zen,
    main_menu_text,
    menu_actions,
    menu_texts,
    onboarding_choice_labels,
    reading_label,
    reading_type_labels,
    readings_menu_text,
    t,
)

BALANCE_BUTTON_PREFIX = "💰 Баланс:"
_OLD_BALANCE_PREFIX = "Баланс:"


def balance_button_text(balance_label: str, lang: str = "ru") -> str:
    return f"{t('btn_balance_prefix', lang)} {balance_label}"


def is_balance_button(text: str) -> bool:
    prefixes = (
        BALANCE_BUTTON_PREFIX,
        _OLD_BALANCE_PREFIX,
        t("btn_balance_prefix", "en"),
        t("btn_balance_prefix", "es"),
        t("btn_balance_prefix", "pt"),
    )
    return any(text.startswith(prefix) for prefix in prefixes)


READING_TYPE_LABELS = reading_type_labels()


def _plain_label(label: str) -> str:
    return label.split(" ", 1)[1] if " " in label and not label[0].isalnum() else label


def _build_reading_label_map() -> dict[str, str]:
    from app.bot.i18n import SUPPORTED_LANGUAGES, reading_label_to_type

    mapping: dict[str, str] = {}
    for lang in SUPPORTED_LANGUAGES:
        mapping.update(reading_label_to_type(lang))
    return mapping


READING_LABEL_TO_TYPE = _build_reading_label_map()

from app.bot.i18n_extra import ONBOARDING_CHOICE_KEYS
from app.services.billing.limits import HISTORY_PAGE_SIZE, MEMORY_PAGE_SIZE

# Обратная совместимость для импортов
BTN_READINGS = btn_readings()
BTN_DAILY = btn_daily()
BTN_HISTORY = btn_history()
BTN_INFO = btn_info()
BTN_SUPPORT = btn_support()
BTN_SETTINGS = btn_settings()
BTN_ZEN = btn_zen()
BTN_ENERGY = btn_energy()

MENU_ACTIONS = menu_actions()
MENU_TEXTS = menu_texts()
MAIN_MENU_TEXT = main_menu_text()
READINGS_MENU_TEXT = readings_menu_text()


def main_menu(balance_label: str = "0 ₽", lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=balance_button_text(balance_label, lang))],
            [KeyboardButton(text=btn_readings(lang)), KeyboardButton(text=btn_daily(lang))],
            [KeyboardButton(text=btn_zen(lang)), KeyboardButton(text=btn_energy(lang))],
            [KeyboardButton(text=btn_history(lang)), KeyboardButton(text=btn_language(lang))],
            [KeyboardButton(text=btn_info(lang)), KeyboardButton(text=btn_support(lang))],
            [KeyboardButton(text=btn_settings(lang))],
        ],
        resize_keyboard=True,
    )


def _support_button(lang: str = "ru") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t("btn_support", lang), url=support_url())


def _legal_button(lang: str = "ru") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t("btn_legal", lang), url=LEGAL_URL)


def _home_button(lang: str = "ru") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t("btn_home", lang), callback_data="nav:back:main")


def _back_button(target: str, lang: str = "ru") -> InlineKeyboardButton:
    if target == "main":
        return _home_button(lang)
    return InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"nav:back:{target}")


def _pagination_buttons(prefix: str, page: int, total_pages: int, lang: str = "ru") -> list[InlineKeyboardButton]:
    buttons: list[InlineKeyboardButton] = []
    if page > 0:
        buttons.append(
            InlineKeyboardButton(text=t("btn_pagination_back", lang), callback_data=f"{prefix}:{page - 1}")
        )
    if page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(text=t("btn_pagination_forward", lang), callback_data=f"{prefix}:{page + 1}")
        )
    return buttons


def inline_main_menu(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=btn_readings(lang), callback_data="nav:readings"),
                InlineKeyboardButton(text=btn_daily(lang), callback_data="nav:daily"),
            ],
            [
                InlineKeyboardButton(text=btn_zen(lang), callback_data="nav:zen"),
                InlineKeyboardButton(text=btn_energy(lang), callback_data="nav:energy"),
            ],
            [
                InlineKeyboardButton(text=btn_history(lang), callback_data="nav:history"),
                InlineKeyboardButton(text=t("btn_topup", lang), callback_data="nav:billing"),
            ],
            [
                InlineKeyboardButton(text=btn_language(lang), callback_data="nav:language"),
                InlineKeyboardButton(text=btn_info(lang), callback_data="nav:info"),
            ],
            [
                InlineKeyboardButton(text=btn_settings(lang), callback_data="nav:settings"),
                _support_button(lang),
            ],
            [InlineKeyboardButton(text=t("btn_referrals", lang), callback_data="nav:referrals")],
        ]
    )


def inline_readings_menu(lang: str = "ru") -> InlineKeyboardMarkup:
    labels = reading_type_labels(lang)
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for key, label in labels.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"nav:reading:{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_home_button(lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_reading_prompt(reading_type: str, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_back_button("readings", lang)],
            [_home_button(lang)],
        ]
    )


def inline_profile_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Данные анкеты", callback_data="nav:profile_edit")],
            [
                InlineKeyboardButton(text="🔮 Сделать расклад", callback_data="nav:readings"),
                InlineKeyboardButton(text="🌅 Карта дня", callback_data="nav:daily"),
            ],
            [
                InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="nav:billing"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="nav:settings"),
            ],
            [
                InlineKeyboardButton(text="📜 История раскладов", callback_data="nav:history"),
                InlineKeyboardButton(text="🤝 Пригласить друга · 40%", callback_data="nav:referrals"),
            ],
            [_home_button()],
        ]
    )


def inline_info_menu(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_legal_button(lang)],
            [_support_button(lang)],
            [_home_button(lang)],
        ]
    )


def inline_settings_menu(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_profile_data", lang), callback_data="nav:profile_edit")],
            [InlineKeyboardButton(text=btn_language(lang), callback_data="nav:language")],
            [InlineKeyboardButton(text=t("btn_memory", lang), callback_data="mem:page:0")],
            [InlineKeyboardButton(text=t("btn_change_voice", lang), callback_data="set:voice")],
            [InlineKeyboardButton(text=t("btn_change_timezone", lang), callback_data="set:timezone")],
            [
                InlineKeyboardButton(text=t("btn_toggle_daily", lang), callback_data="set:toggle:daily"),
                InlineKeyboardButton(text=t("btn_toggle_proactive", lang), callback_data="set:toggle:proactive"),
            ],
            [_home_button(lang)],
        ]
    )


def inline_language_menu(current: str = "ru") -> InlineKeyboardMarkup:
    from app.bot.i18n import LANGUAGE_LABELS, SUPPORTED_LANGUAGES

    rows: list[list[InlineKeyboardButton]] = []
    for code in SUPPORTED_LANGUAGES:
        label = LANGUAGE_LABELS[code]
        prefix = "✓ " if code == current else ""
        rows.append(
            [InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"set:lang:{code}")]
        )
    rows.append([_home_button(current)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _profile_button_text(label: str, value: str) -> str:
    text = f"{label}: {value}"
    return text if len(text) <= 60 else f"{text[:57]}…"


def inline_memory_list_menu(memories: list, page: int, total_pages: int, lang: str = "ru") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    start = page * MEMORY_PAGE_SIZE
    for index, memory in enumerate(memories, start=start + 1):
        preview = memory.description.strip().replace("\n", " ")
        if len(preview) > 36:
            preview = preview[:36] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{index}. {preview}",
                    callback_data=f"mem:open:{memory.id}:{page}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t("btn_memory_add", lang), callback_data=f"mem:add:{page}")])
    nav = _pagination_buttons("mem:page", page, total_pages, lang)
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=t("btn_back_to_settings", lang), callback_data="nav:settings")])
    rows.append([_home_button(lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_memory_empty_menu(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_memory_add", lang), callback_data="mem:add:0")],
            [InlineKeyboardButton(text=t("btn_back_to_settings", lang), callback_data="nav:settings")],
            [_home_button(lang)],
        ]
    )


def inline_memory_detail_menu(memory_id: str, page: int, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_memory_delete", lang), callback_data=f"mem:del:{memory_id}:{page}")],
            [InlineKeyboardButton(text=t("btn_back_to_list", lang), callback_data=f"mem:page:{page}")],
            [InlineKeyboardButton(text=t("btn_back_to_settings", lang), callback_data="nav:settings")],
            [_home_button(lang)],
        ]
    )


def inline_profile_edit_menu(rows: list[tuple[str, str, str]], lang: str = "ru") -> InlineKeyboardMarkup:
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
    buttons.append([InlineKeyboardButton(text=t("btn_back_to_settings_long", lang), callback_data="nav:settings")])
    buttons.append([_home_button(lang)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def profile_field_keyboard(field_key: str, lang: str = "ru") -> InlineKeyboardMarkup | None:
    options = onboarding_choice_labels(field_key, lang) if field_key in ONBOARDING_CHOICE_STEPS else None
    if not options:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t("btn_back", lang), callback_data="nav:profile_edit")],
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
    rows.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="nav:profile_edit")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_billing_menu(lang: str = "ru") -> InlineKeyboardMarkup:
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
            [InlineKeyboardButton(text=t("btn_spending_history", lang), callback_data="bill:spend:0")],
            [_support_button(lang)],
            [InlineKeyboardButton(text=t("btn_referral_program", lang), callback_data="nav:referrals")],
            [_home_button(lang)],
        ]
    )


def inline_spending_menu(page: int, total_pages: int, lang: str = "ru") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    nav = _pagination_buttons("bill:spend", page, total_pages, lang)
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=t("btn_back_to_billing", lang), callback_data="nav:billing")])
    rows.append([_home_button(lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_referral_menu(*, share_link: str | None = None, lang: str = "ru") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=t("btn_my_invite_link", lang), callback_data="ref:share")],
    ]
    if share_link:
        share_text = t("share_referral_text", lang)
        share_url = (
            "https://t.me/share/url?"
            f"url={quote(share_link)}&text={quote(share_text)}"
        )
        rows.append(
            [InlineKeyboardButton(text=t("btn_share_friend", lang), url=share_url)]
        )
    rows.append([InlineKeyboardButton(text=t("btn_withdraw", lang), callback_data="ref:withdraw")])
    rows.append([_home_button(lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_withdraw_wallet_menu(saved_wallet: str | None, lang: str = "ru") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if saved_wallet:
        short = f"{saved_wallet[:6]}…{saved_wallet[-4:]}"
        rows.append(
            [InlineKeyboardButton(text=t("btn_wallet_saved", lang, short=short), callback_data="ref:wallet_saved")]
        )
    rows.append([InlineKeyboardButton(text=t("btn_wallet_new", lang), callback_data="ref:wallet_new")])
    rows.append([_home_button(lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_history_menu(readings: list, page: int, total_pages: int, lang: str = "ru") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    start = page * HISTORY_PAGE_SIZE
    for index, reading in enumerate(readings, start=start + 1):
        label = reading_label(reading.reading_type, lang)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{index}. {label}",
                    callback_data=f"hist:open:{reading.id}",
                )
            ]
        )
    nav = _pagination_buttons("hist:page", page, total_pages, lang)
    if nav:
        rows.append(nav)
    rows.append([_home_button(lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_photo_mode_menu(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("photo_mode_aura", lang), callback_data="photo:mode:aura")],
            [InlineKeyboardButton(text=t("photo_mode_palm", lang), callback_data="photo:mode:palm")],
            [InlineKeyboardButton(text=t("photo_mode_custom", lang), callback_data="photo:mode:other")],
            [_home_button(lang)],
        ]
    )


def onboarding_keyboard(step_key: str, lang: str = "ru") -> InlineKeyboardMarkup | None:
    if step_key not in ONBOARDING_CHOICE_STEPS:
        return None

    options = onboarding_choice_labels(step_key, lang)
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for option in options:
        row.append(InlineKeyboardButton(text=option, callback_data=f"onb:pick:{step_key}:{option}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="onb:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_zen_menu(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("zen_btn_daily", lang), callback_data="nav:zen:daily")],
            [InlineKeyboardButton(text=t("zen_btn_ask", lang), callback_data="nav:zen:ask")],
            [_home_button(lang)],
        ]
    )


def inline_zen_prompt(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_back_button("zen", lang)],
            [_home_button(lang)],
        ]
    )


def inline_energy_menu(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("energy_btn_runes", lang), callback_data="nav:energy:runes")],
            [InlineKeyboardButton(text=t("energy_btn_stones", lang), callback_data="nav:energy:stones")],
            [InlineKeyboardButton(text=t("energy_btn_bracelet", lang), callback_data="nav:energy:bracelet")],
            [_home_button(lang)],
        ]
    )


def inline_rune_prompt(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_back_button("energy", lang)],
            [_home_button(lang)],
        ]
    )


def inline_stone_prompt(lang: str = "ru") -> InlineKeyboardMarkup:
    return inline_rune_prompt(lang)


def inline_bracelet_prompt(lang: str = "ru") -> InlineKeyboardMarkup:
    return inline_rune_prompt(lang)
