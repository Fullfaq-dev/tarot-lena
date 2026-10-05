"""Куда вернуть после оплаты: тот разбор, который только что проходили.

Robokassa в кабинете часто держит SuccessURL=/lk — «вернуться в магазин»
не должен требовать логин и не должен терять разбор.
"""


def pick_return_token(*, shp_token: str = "", payment_token: str = "", cookie_token: str = "") -> str:
    for item in (shp_token, payment_token, cookie_token):
        value = (item or "").strip()
        if value:
            return value
    return ""


def reading_return_path(token: str) -> str:
    return f"/r/{token}?paid=1"


def is_robokassa_return_path(path: str) -> bool:
    clean = (path or "").split("?")[0].rstrip("/") or "/"
    return clean in {"/lk", "/payment/success", "/payment/failed"} or clean.startswith("/lk")


def bypass_login_return_path(*, path: str, shp_token: str = "", payment_token: str = "", cookie_token: str = "") -> str:
    token = pick_return_token(shp_token=shp_token, payment_token=payment_token, cookie_token=cookie_token)
    if token and is_robokassa_return_path(path):
        return reading_return_path(token)
    if token and not (path or "").startswith("/r/"):
        return reading_return_path(token)
    return ""
