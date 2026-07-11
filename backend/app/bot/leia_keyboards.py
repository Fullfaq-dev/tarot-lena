from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.bot.leia_texts import BTN_MENU, BTN_PROFILE, legal_url
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
    rows.append([InlineKeyboardButton(text="📦 Пакеты и подписки", callback_data="leia:packages")])
    rows.append([InlineKeyboardButton(text="👭 Приведи подругу", callback_data="leia:referral")])
    rows.append([InlineKeyboardButton(text="👤 Профиль", callback_data="leia:profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_product_actions(product_id: str, *, access_label: str | None = None) -> InlineKeyboardMarkup:
    product = PRODUCTS[product_id]
    price = int(product.price_rub)
    rows = []
    if access_label:
        rows.append(
            [InlineKeyboardButton(text="▶️ Запустить", callback_data=f"leia:launch:{product_id}")]
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


def leia_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MENU), KeyboardButton(text=BTN_PROFILE)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
