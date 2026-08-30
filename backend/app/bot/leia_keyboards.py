from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.bot.leia_texts import BTN_HISTORY, BTN_MENU, BTN_PROFILE, legal_url
from app.services.products.catalog import PRODUCTS
from app.services.products.packages import PACKAGES


def inline_legal_consent() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Соглашаюсь", callback_data="leia:consent")],
        ]
    )


def inline_skip_birth_time() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="leia:skip_time")],
        ]
    )


def inline_gender_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👩 Женский", callback_data="leia:gender:female"),
                InlineKeyboardButton(text="👨 Мужской", callback_data="leia:gender:male"),
            ],
            [InlineKeyboardButton(text="⏭ Не указывать", callback_data="leia:gender:skip")],
        ]
    )


def inline_profile_actions() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить", callback_data="leia:edit_profile")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="leia:menu")],
            [InlineKeyboardButton(text="📦 Пакеты", callback_data="leia:packages")],
        ]
    )


def inline_leia_edit_menu() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Имя", callback_data="leia:edit:name"),
            InlineKeyboardButton(text="Пол", callback_data="leia:edit:gender"),
        ],
        [
            InlineKeyboardButton(text="Дата рождения", callback_data="leia:edit:birth_date"),
            InlineKeyboardButton(text="Время рождения", callback_data="leia:edit:birth_time"),
        ],
        [InlineKeyboardButton(text="Город рождения", callback_data="leia:edit:birth_city")],
        [InlineKeyboardButton(text="◀️ К профилю", callback_data="leia:profile")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_product_menu() -> InlineKeyboardMarkup:
    rows = []
    for product in PRODUCTS.values():
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{product.emoji} {product.title}",
                    callback_data=f"leia:product:{product.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="📜 История разборов", callback_data="leia:history:0")])
    rows.append([InlineKeyboardButton(text="📦 Пакеты и подписки", callback_data="leia:packages")])
    rows.append([InlineKeyboardButton(text="👭 Приведи подругу", callback_data="leia:referral")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_history_menu(
    items: list,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        product = PRODUCTS.get(item.product_id)
        title = f"{product.emoji} {product.title}" if product else item.product_id
        level = "мини" if item.level == "mini" else "полная"
        when = item.created_at.strftime("%d.%m %H:%M") if item.created_at else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{title} · {level} · {when}",
                    callback_data=f"leia:hist:{item.id}",
                )
            ]
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"leia:history:{page - 1}"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"leia:history:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="leia:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_history_item() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📜 К истории", callback_data="leia:history:0")],
            [InlineKeyboardButton(text="💬 Вопрос к разбору", callback_data="leia:followup")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="leia:menu")],
        ]
    )


def inline_payment_button(
    url: str,
    *,
    amount_rub: str | int | None = None,
    package: bool = False,
) -> InlineKeyboardMarkup:
    if amount_rub is not None:
        label = f"💳 Оплатить {amount_rub} ₽"
    elif package:
        label = "💳 Оплатить пакет"
    else:
        label = "💳 Оплатить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, url=url)],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="leia:menu")],
        ]
    )


def inline_product_actions(
    product_id: str,
    *,
    access_label: str | None = None,
    mini_used: bool = False,
) -> InlineKeyboardMarkup:
    product = PRODUCTS[product_id]
    price = int(product.price_rub)
    rows = []
    if access_label:
        rows.append(
            [InlineKeyboardButton(text="▶️ Запустить", callback_data=f"leia:launch:{product_id}")]
        )
    else:
        if mini_used:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="🆓 Мини уже была",
                        callback_data=f"leia:mini_used:{product_id}",
                    )
                ]
            )
        else:
            rows.append(
                [InlineKeyboardButton(text="🆓 Мини-версия", callback_data=f"leia:mini:{product_id}")]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🔓 Полная — {price} ₽",
                    callback_data=f"leia:full:{product_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="leia:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_after_mini(product_id: str, *, access_label: str | None = None) -> InlineKeyboardMarkup:
    product = PRODUCTS[product_id]
    price = int(product.price_rub)
    if access_label:
        full_label = "▶️ Запустить"
        callback = f"leia:launch:{product_id}"
    else:
        full_label = f"🔓 Полная расшифровка — {price} ₽"
        callback = f"leia:full:{product_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=full_label, callback_data=callback)],
            [InlineKeyboardButton(text="◀️ Меню", callback_data="leia:menu")],
        ]
    )


def inline_after_full_reading() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Задать вопрос к разбору", callback_data="leia:followup")],
            [InlineKeyboardButton(text="📦 Тарифы и пакеты", callback_data="leia:packages")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="leia:menu")],
        ]
    )


def inline_packages_menu() -> InlineKeyboardMarkup:
    rows = []
    for package in PACKAGES.values():
        price = int(package.price_rub)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{package.emoji} {package.title} — {price} ₽",
                    callback_data=f"leia:package:{package.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ Меню", callback_data="leia:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_package_actions(package_id: str, *, active: bool = False) -> InlineKeyboardMarkup:
    package = PACKAGES[package_id]
    price = int(package.price_rub)
    if active:
        rows = [
            [InlineKeyboardButton(text="▶️ Запустить — выбери продукт", callback_data="leia:menu")],
            [InlineKeyboardButton(text="◀️ Пакеты", callback_data="leia:packages")],
        ]
    else:
        rows = [
            [
                InlineKeyboardButton(
                    text=f"💳 Купить — {price} ₽",
                    callback_data=f"leia:buy:{package_id}",
                )
            ],
            [InlineKeyboardButton(text="◀️ Пакеты", callback_data="leia:packages")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_referral_share(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={link}")],
            [InlineKeyboardButton(text="◀️ Меню", callback_data="leia:menu")],
        ]
    )


def inline_legal_links() -> InlineKeyboardMarkup:
    url = legal_url()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Документы", url=url)],
            [InlineKeyboardButton(text="✅ Соглашаюсь", callback_data="leia:consent")],
        ]
    )


def inline_funnel_day2_topics() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❤️ Отношения", callback_data="leia:funnel:love"),
                InlineKeyboardButton(text="💰 Деньги", callback_data="leia:funnel:wealth"),
            ],
            [InlineKeyboardButton(text="🔮 Просто совет", callback_data="leia:funnel:advice")],
        ]
    )


def inline_evening_reading() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌙 Вечерний расклад", callback_data="leia:evening_reading")],
        ]
    )


def inline_chat_collect() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="leia:chat_done")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="leia:menu")],
        ]
    )


def inline_broadcast_products() -> InlineKeyboardMarkup:
    """Кнопки продуктов — для рассылок."""
    p = PRODUCTS
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{p['tarot_spread'].emoji} {p['tarot_spread'].title}",
                    callback_data="leia:product:tarot_spread",
                ),
                InlineKeyboardButton(
                    text=f"{p['love'].emoji} {p['love'].title}",
                    callback_data="leia:product:love",
                ),
                InlineKeyboardButton(
                    text=f"{p['chat'].emoji} {p['chat'].title}",
                    callback_data="leia:product:chat",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"{p['wealth'].emoji} {p['wealth'].title}",
                    callback_data="leia:product:wealth",
                ),
                InlineKeyboardButton(
                    text=f"{p['negative'].emoji} {p['negative'].title}",
                    callback_data="leia:product:negative",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"{p['forecast'].emoji} {p['forecast'].title}",
                    callback_data="leia:product:forecast",
                ),
                InlineKeyboardButton(
                    text=f"{p['question'].emoji} {p['question'].title}",
                    callback_data="leia:product:question",
                ),
            ],
        ]
    )


def leia_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MENU), KeyboardButton(text=BTN_HISTORY)],
            [KeyboardButton(text=BTN_PROFILE)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
