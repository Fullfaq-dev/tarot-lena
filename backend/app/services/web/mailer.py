"""Optional SMTP. If not configured, only log."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_reading_link(to_email: str, token: str) -> None:
    settings = get_settings()
    url = f"{settings.public_base_url.rstrip('/')}/r/{token}"
    if not settings.smtp_host or not settings.smtp_from:
        logger.info("SMTP skipped, reading link for %s: %s", to_email, url)
        return
    msg = EmailMessage()
    msg["Subject"] = "Лея — ссылка на разбор"
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(
        "Твой разбор сохранён. Ссылка живёт год:\n\n"
        f"{url}\n\n"
        "Если письмо пришло по ошибке — проигнорируй."
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except Exception:
        logger.exception("SMTP send failed to %s", to_email)
