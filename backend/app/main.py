import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.admin_api.router import router as admin_router
from app.admin_api.auth_router import router as admin_auth_router
from app.admin_api.auth import ensure_bootstrap_admin
from app.api.health import router as health_router
from app.api.kie_callbacks import router as kie_callbacks_router
from app.api.platega_callbacks import router as platega_callbacks_router
from app.bot.factory import create_bot, create_dispatcher
from app.core.config import get_settings
from app.services.tarot.seed import ensure_tarot_cards_seeded

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task] = set()


def _spawn_update_handler(bot, dispatcher, update: Update) -> None:
    task = asyncio.create_task(dispatcher.feed_update(bot, update))
    _background_tasks.add(task)

    def _done(done_task: asyncio.Task) -> None:
        _background_tasks.discard(done_task)
        try:
            done_task.result()
        except Exception:
            logger.exception("Telegram update handler failed")

    task.add_done_callback(_done)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.tarot_cards_dir.mkdir(parents=True, exist_ok=True)
    await ensure_tarot_cards_seeded()
    await ensure_bootstrap_admin()
    app.state.bot = create_bot()
    app.state.dispatcher = create_dispatcher()
    if (
        settings.app_env != "local"
        and settings.telegram_bot_token != "replace-me"
        and settings.public_base_url.startswith("https://")
    ):
        try:
            await app.state.bot.set_webhook(
                settings.webhook_url,
                secret_token=settings.telegram_webhook_secret,
                drop_pending_updates=False,
            )
        except Exception as exc:
            logger.warning("Telegram webhook not configured: %s", exc)
    yield
    if _background_tasks:
        logger.info("Waiting for %s background telegram tasks", len(_background_tasks))
        await asyncio.gather(*_background_tasks, return_exceptions=True)
    await app.state.bot.session.close()


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(kie_callbacks_router)
app.include_router(platega_callbacks_router)
app.include_router(admin_auth_router, prefix="/admin-api/auth")
app.include_router(admin_router, prefix="/admin-api")

settings = get_settings()
settings.media_storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/tarot_cards", StaticFiles(directory=str(settings.tarot_cards_dir)), name="tarot_cards")
app.mount("/static/generated", StaticFiles(directory=str(settings.media_storage_dir)), name="generated")


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    settings = get_settings()
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid Telegram secret")

    update = Update.model_validate(await request.json(), context={"bot": request.app.state.bot})
    _spawn_update_handler(request.app.state.bot, request.app.state.dispatcher, update)
    return {"ok": True}
