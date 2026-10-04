"""Куда вернуть после оплаты: тот разбор, который только что проходили."""


def pick_return_token(*, shp_token: str = "", payment_token: str = "", cookie_token: str = "") -> str:
    for item in (shp_token, payment_token, cookie_token):
        value = (item or "").strip()
        if value:
            return value
    return ""


def reading_return_path(token: str) -> str:
    return f"/r/{token}?paid=1"
