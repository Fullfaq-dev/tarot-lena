from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.bot.handlers import register_handlers
from app.bot.middleware import LocaleSyncMiddleware
from app.core.config import get_settings


def create_bot() -> Bot:
    settings = get_settings()
    return Bot(token=settings.telegram_bot_token)


def create_dispatcher() -> Dispatcher:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    dispatcher = Dispatcher(storage=RedisStorage(redis=redis))
    dispatcher.update.middleware(LocaleSyncMiddleware())
    register_handlers(dispatcher)
    return dispatcher
