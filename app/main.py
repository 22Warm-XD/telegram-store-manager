from __future__ import annotations

import asyncio

from aiogram import Dispatcher
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.bot import create_bot, create_dispatcher
from app.config import load_settings
from app.database.session import create_engine
from app.utils.logging import configure_logging, get_logger


async def on_startup(dispatcher: Dispatcher) -> None:
    logger = get_logger("app.startup")
    logger.info("bot_starting")


async def on_shutdown(dispatcher: Dispatcher, bot, engine: AsyncEngine) -> None:
    logger = get_logger("app.shutdown")
    logger.info("bot_stopping")
    await dispatcher.storage.close()
    await bot.session.close()
    await engine.dispose()


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    logger = get_logger("app.main")

    engine = create_engine(settings)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    bot = create_bot(settings)
    dispatcher = create_dispatcher(settings=settings, session_factory=session_factory)
    dispatcher.startup.register(on_startup)

    async def shutdown_handler(dispatcher_: Dispatcher) -> None:
        await on_shutdown(dispatcher_, bot, engine)

    dispatcher.shutdown.register(shutdown_handler)

    logger.info("polling_started")
    await bot.delete_webhook(drop_pending_updates=False)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
