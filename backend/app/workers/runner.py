import asyncio
import signal

from app.services.notifications.scheduler import NotificationScheduler


async def main() -> None:
    stop = asyncio.Event()

    def _stop() -> None:
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _stop)

    scheduler = NotificationScheduler()
    while not stop.is_set():
        await scheduler.tick()
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
