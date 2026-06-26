# Arcana AI Project

## Stack

- Backend: Python 3.12, FastAPI, aiogram 3, SQLAlchemy async, asyncpg, Alembic, Redis FSM storage.
- AI/media providers: KIE.ai chat and image jobs, 302.ai STT, ElevenLabs TTS.
- Payments: Platega via local SDK, balance and subscription records in PostgreSQL.
- Frontend assets: static landing/legal site in `site/`, admin SPA in `frontend-admin`.
- Production: Docker Compose on VPS, nginx serves `site/` and proxies API/admin routes.

## Architecture

- Telegram bot handlers live in `backend/app/bot/handlers.py`; user-facing texts are centralized in i18n modules.
- Services encapsulate business logic under `backend/app/services/*`.
- Database models live in `backend/app/database/models.py`; schema changes require Alembic migrations.
- Static public website is mounted by nginx from `site/` and should remain dependency-free.
- Owner notifications are sent through `app.services.telegram_notify.notify_owner`.

## Naming And Change Rules

- Keep bot start payloads short and explicit, e.g. `landing`, `ref_<id>`.
- Preserve public/legal pages when changing the website.
- Use existing service and helper patterns instead of adding framework dependencies.
- Track task progress in `openspec/progress.md`.
