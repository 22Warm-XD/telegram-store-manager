from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisEventIsolation, RedisStorage
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.handlers.admin import active_products, add_product, admin_panel, discount, import_channel, sold
from app.handlers.user import catalog, fallback, start, support
from app.middlewares.session import DatabaseSessionMiddleware
from app.middlewares.user_sync import UserSyncMiddleware


def create_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(
    *,
    settings: Settings,
    session_factory: async_sessionmaker,
) -> Dispatcher:
    redis = Redis.from_url(settings.redis_dsn)
    storage = RedisStorage(redis=redis)
    events_isolation = RedisEventIsolation(redis=redis)
    dispatcher = Dispatcher(storage=storage, events_isolation=events_isolation)

    dispatcher.update.outer_middleware(DatabaseSessionMiddleware(session_factory=session_factory, settings=settings))
    dispatcher.update.middleware(UserSyncMiddleware())

    dispatcher.include_router(admin_panel.router)
    dispatcher.include_router(add_product.router)
    dispatcher.include_router(import_channel.router)
    dispatcher.include_router(discount.router)
    dispatcher.include_router(active_products.router)
    dispatcher.include_router(sold.router)

    dispatcher.include_router(start.router)
    dispatcher.include_router(support.router)
    dispatcher.include_router(catalog.router)
    dispatcher.include_router(fallback.router)
    return dispatcher
