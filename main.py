import asyncio
import logging
import signal

from apiserver import start_api, stop_api
from feishubot import start_bot, stop_bot
from utils.config_vars import LOG_LEVEL, sql


def _setup_logging() -> None:
    logging.basicConfig(
        level=LOG_LEVEL.upper(),
        format="[%(levelname)s]%(asctime)s: %(message)s",
        handlers=[
            logging.FileHandler("data/run.log", encoding="UTF-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> None:
    _setup_logging()
    sql.create_users_db()
    sql.create_subscribe_db()

    start_api()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    stop_event = asyncio.Event()

    def _graceful_stop(*_args):
        loop.call_soon_threadsafe(stop_event.set)

    try:
        loop.add_signal_handler(signal.SIGINT, _graceful_stop)
        loop.add_signal_handler(signal.SIGTERM, _graceful_stop)
    except NotImplementedError:
        # Windows 不支持，退回 KeyboardInterrupt 路径
        pass

    async def _runner():
        bot_task = asyncio.create_task(start_bot())
        stop_task = asyncio.create_task(stop_event.wait())
        done, pending = await asyncio.wait(
            {bot_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
        await stop_bot()

    try:
        loop.run_until_complete(_runner())
    except KeyboardInterrupt:
        loop.run_until_complete(stop_bot())
    finally:
        stop_api()
        sql.close()
        loop.close()


if __name__ == "__main__":
    main()
