# ADR-003: Деплой по IP без домена — polling вместо webhook

**Статус:** Принято  
**Дата:** 2026-07-06

## Контекст

VPS Zeabur: `43.165.5.18`, домена пока нет. Telegram Bot API требует **HTTPS** для webhook. Platega callback тоже предпочтительно на HTTPS.

## Решение

### Telegram (MVP)

Запускать бота в режиме **long polling** (`python -m app.bot.polling`), а не webhook:

- В `docker-compose.prod.yml` сервис `bot` с профилем `polling` — **включить по умолчанию** для tarot-lena.
- Сервис `api` **не** вызывает `set_webhook` при старте (флаг `TELEGRAM_USE_POLLING=1` или отсутствие валидного HTTPS URL).

### HTTP-сервисы на IP

- `PUBLIC_BASE_URL=http://43.165.5.18`
- nginx `server_name 43.165.5.18;` — только порт 80, без SSL.
- Лендинг, legal, admin panel, health, payment return pages — по HTTP.

### Platega

- Return URL: `http://43.165.5.18/payment/success` и `/payment/failed`.
- Callback webhook: уточнить у Platega, принимают ли HTTP. Если нет — временно проверка статуса платежа по polling/cron или ждать домен.

### Когда появится домен

1. DNS A-запись → `43.165.5.18`
2. certbot + `deploy/retry-ssl.sh`
3. Переключить на webhook, отключить polling-контейнер.

## Последствия

- Два процесса: `api` (FastAPI) + `bot` (polling worker) вместо одного webhook.
- Рассылки и scheduler остаются в `worker` — без изменений.
