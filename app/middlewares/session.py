from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.database.repositories.products import AdminActionLogRepository, ProductRepository
from app.database.repositories.store_settings import StoreSettingsRepository
from app.database.repositories.users import UserRepository
from app.services.channel_service import ChannelService
from app.services.product_service import ProductService
from app.services.store_settings_service import StoreSettingsService


class DatabaseSessionMiddleware(BaseMiddleware):
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker,
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            products_repo = ProductRepository(session)
            users_repo = UserRepository(session)
            admin_logs_repo = AdminActionLogRepository(session)
            store_settings_repo = StoreSettingsRepository(session)
            channel_service = ChannelService(bot=data["bot"], settings=self.settings)
            product_service = ProductService(
                session=session,
                products=products_repo,
                admin_logs=admin_logs_repo,
                channel_service=channel_service,
            )
            store_settings_service = StoreSettingsService(session=session, repository=store_settings_repo)

            data.update(
                {
                    "session": session,
                    "products_repo": products_repo,
                    "users_repo": users_repo,
                    "admin_logs_repo": admin_logs_repo,
                    "channel_service": channel_service,
                    "product_service": product_service,
                    "store_settings_service": store_settings_service,
                    "settings": self.settings,
                }
            )
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
