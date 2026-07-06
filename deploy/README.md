# Deploy — Tarot Lena (бот «Лея»)

## GitHub

Repository: https://github.com/Fullfaq-dev/tarot-lena

Autodeploy runs on every push to `main` via `.github/workflows/deploy.yml`.

Required GitHub secrets:

- `VPS_HOST` — `43.165.5.18`
- `VPS_USER` — `ubuntu`
- `VPS_SSH_KEY` — private deploy key
- `TELEGRAM_BOT_TOKEN` — токен @astro_leia_bot
- `KIE_API_KEY` — ключ KIE.ai
- `PLATEGA_MERCHANT_ID`, `PLATEGA_API_KEY` — Platega (опционально; без них включён демо-режим оплаты)

Скопируйте secrets из репозитория `arcane-ai` (Settings → Secrets) в `tarot-lena`.

## Демо-оплата

`PAYMENTS_DEMO_MODE=1` (по умолчанию) — кнопка «Купить» сразу проводит платёж на указанную сумму без Platega.
Когда добавите ключи Platega в secrets, CI автоматически выставит `PAYMENTS_DEMO_MODE=0`.

## Server layout

- App path: `/opt/tarot-lena`
- Env file: `/opt/tarot-lena/.env` (not in git)
- Compose: `docker-compose.prod.yml`
- Telegram: **long polling** (контейнер `bot`), webhook — после появления домена

Manual deploy on server:

```bash
cd /opt/tarot-lena
bash deploy/deploy.sh
```

## URLs (IP-only MVP)

- Site: `http://43.165.5.18:8080/`
- Legal: `http://43.165.5.18:8080/legal`
- Admin: `http://43.165.5.18:8080/panel/`
- API health: `http://43.165.5.18:8080/health`
- Bot: https://t.me/astro_leia_bot

## First-time server setup

```bash
# On VPS as ubuntu
sudo bash deploy/setup-server.sh
# Configure .env, then:
bash deploy/deploy.sh
```

## Platega callback URL

```
http://43.165.5.18:8080/callbacks/platega
```

Return URLs:

- Success: `http://43.165.5.18:8080/payment/success`
- Failed: `http://43.165.5.18:8080/payment/failed`

**Note:** Port 80/443 заняты Zeabur proxy — наш nginx на **8080**.

## Domain (later)

When a domain is available:

1. DNS A-record → `43.165.5.18`
2. Run `bash deploy/retry-ssl.sh`
3. Set `PUBLIC_BASE_URL=https://<domain>`, `TELEGRAM_USE_POLLING=0`
4. Restart `api`, stop `bot` container (webhook mode)
