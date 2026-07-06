from app.core.config import get_settings


def legal_url() -> str:
    return get_settings().legal_page_url


LEGAL_URL = legal_url()


def support_url() -> str:
    return get_settings().support_telegram_url


def info_panel_text(lang: str = "ru") -> str:
    from app.bot.i18n import t

    return t("info_panel", lang, legal_url=LEGAL_URL)
