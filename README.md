# AI Tarot / Astrology Telegram Bot

Премиальная платформа Telegram-бота по Таро и эзотерике: онбординг, память, Relationship Memory, расклады, AI-ответы через KIE.ai, голос, фото/аура/ладонь, подписки, баланс, рефералка, PDF-отчеты, уведомления и отдельная веб-админка.

## Быстрый Запуск

1. Скопируйте переменные окружения:

```bash
cp .env.example .env
```

2. Заполните `.env`:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `PUBLIC_BASE_URL`
- `KIE_API_KEY`
- `JWT_SECRET`
- параметры Platega, когда будет готов SDK

3. Запустите сервисы:

```bash
docker compose up --build
```

4. Примените миграции:

```bash
docker compose exec api alembic upgrade head
```

5. Проверьте backend:

```bash
curl http://localhost:8000/health
```

## Основные Модули

- `backend/app/bot` — Telegram handlers, меню, онбординг.
- `backend/app/services/ai` — KIE.ai client, streaming, AI Orchestrator.
- `backend/app/services/memory` — Chat Memory, Long-Term Memory, Soul Profile, Relationship Memory.
- `backend/app/services/tarot` — локальная колода, карта дня, расклады.
- `backend/app/services/billing` — тарифы, баланс, лимиты, Platega adapter.
- `backend/app/services/voice` — Whisper adapter boundary и ElevenLabs TTS через KIE.ai.
- `backend/app/services/vision` — фото, аура, ладонь, инфографика через GPT Image 2.
- `backend/app/services/notifications` — карта дня, реактивации, follow-up по людям.
- `frontend-admin` — отдельная React-админка.

## Карты Таро

AI не генерирует карты. Изображения лежат в папке `Cards-jpg/` в корне проекта — полная колода из 78 карт (JPG) и рубашка `CardBacks.jpg`.

При первом запуске API или бота колода автоматически попадает в таблицу `tarot_cards`. В раскладах бот отправляет изображения выпавших карт.

Переменная окружения:

```text
TAROT_CARDS_DIR=Cards-jpg
```

## Platega

Сейчас платежи идут через интерфейс `PaymentProvider` и тестовый `PlategaProvider`. Когда будет Python SDK, нужно заменить реализацию в:

```text
backend/app/services/billing/providers.py
```

Остальной биллинг менять не нужно: тарифы, баланс, usage accounting и платежные записи уже отделены от провайдера.

## Production

Сборка для VPS:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Перед production запуском:

- настроить домен и HTTPS;
- указать `PUBLIC_BASE_URL`;
- выполнить `alembic upgrade head`;
- собрать админку `npm run build` в `frontend-admin`;
- настроить backup PostgreSQL;
- загрузить реальные изображения карт и placeholder sticker ID.
