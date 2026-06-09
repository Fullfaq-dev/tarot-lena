import asyncio
import signal

from app.bot.factory import create_bot, create_dispatcher
from app.core.config import get_settings
from app.services.tarot.seed import ensure_tarot_cards_seeded


async def main() -> None:
    settings = get_settings()
    settings.tarot_cards_dir.mkdir(parents=True, exist_ok=True)
    await ensure_tarot_cards_seeded()

    bot = create_bot()
    dispatcher = create_dispatcher()
    stop = asyncio.Event()

    def request_stop() -> None:
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, request_stop)

    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dispatcher.start_polling(bot))
    await stop.wait()
    polling_task.cancel()
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
