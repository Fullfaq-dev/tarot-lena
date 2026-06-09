from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.admin_api.router import router as admin_router
from app.api.health import router as health_router
from app.api.kie_callbacks import router as kie_callbacks_router
from app.bot.factory import create_bot, create_dispatcher
from app.core.config import get_settings
from app.services.tarot.seed import ensure_tarot_cards_seeded


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.tarot_cards_dir.mkdir(parents=True, exist_ok=True)
    await ensure_tarot_cards_seeded()
    app.state.bot = create_bot()
    app.state.dispatcher = create_dispatcher()
    if settings.app_env != "local" and settings.telegram_bot_token != "replace-me":
        await app.state.bot.set_webhook(
            settings.webhook_url,
            secret_token=settings.telegram_webhook_secret,
            drop_pending_updates=True,
        )
    yield
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
    await request.app.state.dispatcher.feed_update(request.app.state.bot, update)
    return {"ok": True}
