from __future__ import annotations

import asyncio
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.config import Settings
from app.database.models import Product
from app.database.repositories.users import UserRepository
from app.utils.logging import get_logger
from app.utils.mini_app import build_mini_app_url


class ProductBroadcastService:
    def __init__(self, *, bot: Bot, settings: Settings, users: UserRepository) -> None:
        self.bot = bot
        self.settings = settings
        self.users = users
        self.logger = get_logger("app.product_broadcast")

    async def broadcast_new_product(self, product: Product) -> None:
        order_url = build_mini_app_url(
            self.settings.mini_app_url,
            self.settings.app_version,
            product_id=product.id,
        )
        if not product.photos or not order_url:
            return
        after_id = 0
        sent = skipped = failed = 0
        while recipients := await self.users.list_telegram_ids(after_id=after_id, limit=100):
            after_id = recipients[-1][0]
            for _, telegram_id in recipients:
                try:
                    await self.bot.send_photo(
                        chat_id=telegram_id,
                        photo=product.photos[0].file_id,
                        caption=self._caption(product),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(
                                text="Заказать",
                                web_app=WebAppInfo(url=order_url),
                            )
                        ]]),
                    )
                    sent += 1
                except (TelegramForbiddenError, TelegramBadRequest):
                    skipped += 1
                except Exception:
                    failed += 1
                    self.logger.exception("product_broadcast_delivery_failed", telegram_id=telegram_id, product_id=product.id)
                await asyncio.sleep(0.04)
        self.logger.info("product_broadcast_complete", product_id=product.id, sent=sent, skipped=skipped, failed=failed)

    @staticmethod
    def _caption(product: Product) -> str:
        price = f"<s>{product.old_price:,} ₽</s> {product.price:,} ₽" if product.old_price else f"{product.price:,} ₽"
        description = f"\n{escape(product.description)}" if product.description else ""
        return (
            f"<b>Новый товар: {escape(product.title)}</b>\n"
            f"Размер: {escape(product.size)}\n"
            f"Состояние: {escape(product.condition)}{description}\n"
            f"Цена: <b>{price}</b>"
        ).replace(",", " ")
