# Tarot Lena (бот «Лея»)

> Форк Arcana AI под новый продукт. Репозиторий: `https://github.com/Fullfaq-dev/tarot-lena.git`

## Stack

- Backend: Python 3.12, FastAPI, aiogram 3, SQLAlchemy async, asyncpg, Alembic, Redis FSM storage.
- AI: KIE.ai для генерации текстов (таро, нумерология, астрология).
- Payments: Platega — фиксированные продукты и подписки (без pay-per-token в MVP).
- Frontend: статический лендинг `site/`, admin SPA `frontend-admin`.
- Production: Docker Compose на **новом VPS** (`/opt/tarot-lena`), nginx + SSL.

## Продукт

- Персона: **Лея** — таро, нумерология (Матрица Судьбы / Хшановская), западный зодиак.
- 5 платных продуктов + комбо-пакеты + 2 подписки.
- Бесплатно: утренняя рассылка (1 нед.), нумеропортрет, недельный гороскоп.
- Язык: **ru only** (MVP).

## Architecture

- Handlers: `backend/app/bot/handlers.py` — упрощённое меню из 5 продуктов.
- Products: `backend/app/services/products/` — каталог, entitlements, мини/полная логика.
- Numerology / Astrology: новые сервисы расчёта + AI-интерпретация.
- Funnels / Broadcasts: воронки день 1–2, scheduler утро/вечер/понедельник.
- Prompts: `prompts/system_ru.md`, `numerology_ru.md`, `astro_ru.md`.
- Spec: `openspec/proposals/tarot-lena-migration.md`.

## Naming And Change Rules

- Start payloads: `landing`, `ref_<id>`.
- Payment purposes: `product_*`, `combo_*`, `subscription_*`.
- Токены и секреты — только `.env`, не в git.
- Track progress in `openspec/progress.md`.
