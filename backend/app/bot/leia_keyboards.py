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
    rows.append([InlineKeyboardButton(text="👤 Профиль", callback_data="leia:profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_product_actions(product_id: str, *, access_label: str | None = None) -> InlineKeyboardMarkup:
    product = PRODUCTS[product_id]
    price = int(product.price_rub)
    if access_label:
        full_label = f"✅ Полная — {access_label}"
    else:
        full_label = f"🔓 Полная — {price} ₽"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆓 Мини-версия", callback_data=f"leia:mini:{product_id}")],
            [
                InlineKeyboardButton(
                    text=full_label,
                    callback_data=f"leia:full:{product_id}",
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="leia:menu")],
        ]
    )


def inline_after_mini(product_id: str, *, access_label: str | None = None) -> InlineKeyboardMarkup:
    product = PRODUCTS[product_id]
    price = int(product.price_rub)
    if access_label:
        full_label = f"✅ Полная — {access_label}"
    else:
        full_label = f"🔓 Полная расшифровка — {price} ₽"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=full_label,
                    callback_data=f"leia:full:{product_id}",
                )
            ],
            [InlineKeyboardButton(text="◀️ Меню", callback_data="leia:menu")],
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


def inline_package_actions(package_id: str) -> InlineKeyboardMarkup:
    package = PACKAGES[package_id]
    price = int(package.price_rub)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 Купить — {price} ₽",
                    callback_data=f"leia:buy:{package_id}",
                )
            ],
            [InlineKeyboardButton(text="◀️ Пакеты", callback_data="leia:packages")],
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
