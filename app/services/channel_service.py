from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InputMediaPhoto

from app.config import Settings
from app.database.models import Product
from app.services import formatter
from app.services.exceptions import ChannelOperationError


@dataclass(slots=True)
class ChannelPublishResult:
    channel_message_id: int
    media_group_message_ids: list[int] | None
    channel_chat_id: int | None = None


class ChannelService:
    def __init__(self, *, bot: Bot, settings: Settings) -> None:
        self.bot = bot
        self.settings = settings

    async def publish_product(self, product: Product) -> ChannelPublishResult:
        photos = self._unique_sorted_photos(product)
        if not photos:
            raise ChannelOperationError("Product must have at least one photo to publish.")

        caption = formatter.format_channel_post(product, self.settings.support_username)
        try:
            if len(photos) == 1:
                message = await self.bot.send_photo(
                    chat_id=self.settings.channel_id,
                    photo=photos[0].file_id,
                    caption=caption,
                    parse_mode="HTML",
                )
                return ChannelPublishResult(
                    channel_message_id=message.message_id,
                    media_group_message_ids=None,
                    channel_chat_id=self.settings.channel_id,
                )

            media = [
                InputMediaPhoto(
                    media=photo.file_id,
                    caption=caption if index == 0 else None,
                    parse_mode="HTML" if index == 0 else None,
                )
                for index, photo in enumerate(photos)
            ]
            messages = await self.bot.send_media_group(chat_id=self.settings.channel_id, media=media)
            message_ids = [message.message_id for message in messages]
            return ChannelPublishResult(
                channel_message_id=message_ids[0],
                media_group_message_ids=message_ids,
                channel_chat_id=self.settings.channel_id,
            )
        except TelegramAPIError as exc:
            raise ChannelOperationError("Failed to publish product to channel.") from exc

    async def edit_product_post(self, product: Product) -> ChannelPublishResult:
        await self._edit_caption(
            message_id=product.channel_message_id,
            chat_id=product.channel_chat_id,
            caption=formatter.format_channel_post(product, self.settings.support_username),
        )
        return ChannelPublishResult(
            channel_message_id=product.channel_message_id,
            media_group_message_ids=product.channel_media_group_message_ids,
            channel_chat_id=product.channel_chat_id or self.settings.channel_id,
        )

    async def publish_discount_post(self, product: Product) -> None:
        await self.edit_product_post(product)

    async def mark_product_as_sold(self, product: Product) -> ChannelPublishResult:
        await self._edit_caption(
            message_id=product.channel_message_id,
            chat_id=product.channel_chat_id,
            caption=formatter.format_sold_post(product, self.settings.support_username),
        )
        return ChannelPublishResult(
            channel_message_id=product.channel_message_id,
            media_group_message_ids=product.channel_media_group_message_ids,
            channel_chat_id=product.channel_chat_id or self.settings.channel_id,
        )

    async def _edit_caption(self, *, message_id: int | None, chat_id: int | None, caption: str) -> None:
        if message_id is None:
            raise ChannelOperationError("Product has no channel message id.")
        try:
            await self.bot.edit_message_caption(
                chat_id=chat_id or self.settings.channel_id,
                message_id=message_id,
                caption=caption,
                parse_mode="HTML",
            )
        except TelegramAPIError as exc:
            raise ChannelOperationError("Failed to edit channel post.") from exc

    async def _replace_product_post(self, product: Product, *, caption: str) -> ChannelPublishResult:
        old_message_ids = self._get_message_ids(product)
        result = await self._publish_product_with_caption(product, caption=caption)
        await self._delete_messages(old_message_ids)
        return result

    async def _publish_product_with_caption(
        self,
        product: Product,
        *,
        caption: str,
    ) -> ChannelPublishResult:
        photos = self._unique_sorted_photos(product)
        if not photos:
            raise ChannelOperationError("Product must have at least one photo to publish.")

        try:
            if len(photos) == 1:
                message = await self.bot.send_photo(
                    chat_id=self.settings.channel_id,
                    photo=photos[0].file_id,
                    caption=caption,
                    parse_mode="HTML",
                )
                return ChannelPublishResult(
                    channel_message_id=message.message_id,
                    media_group_message_ids=None,
                    channel_chat_id=self.settings.channel_id,
                )

            media = [
                InputMediaPhoto(
                    media=photo.file_id,
                    caption=caption if index == 0 else None,
                    parse_mode="HTML" if index == 0 else None,
                )
                for index, photo in enumerate(photos)
            ]
            messages = await self.bot.send_media_group(chat_id=self.settings.channel_id, media=media)
            message_ids = [message.message_id for message in messages]
            return ChannelPublishResult(
                channel_message_id=message_ids[0],
                media_group_message_ids=message_ids,
                channel_chat_id=self.settings.channel_id,
            )
        except TelegramAPIError as exc:
            raise ChannelOperationError("Failed to publish replacement product post.") from exc

    def _get_message_ids(self, product: Product) -> list[int]:
        if product.channel_media_group_message_ids:
            return list(product.channel_media_group_message_ids)
        if product.channel_message_id is not None:
            return [product.channel_message_id]
        return []

    def _unique_sorted_photos(self, product: Product):
        unique_photos = []
        seen_file_ids: set[str] = set()
        for photo in sorted(product.photos, key=lambda product_photo: product_photo.sort_order):
            if photo.file_id in seen_file_ids:
                continue
            seen_file_ids.add(photo.file_id)
            unique_photos.append(photo)
        return unique_photos

    async def _delete_messages(self, message_ids: list[int]) -> None:
        try:
            for message_id in message_ids:
                await self.bot.delete_message(chat_id=self.settings.channel_id, message_id=message_id)
        except TelegramAPIError as exc:
            raise ChannelOperationError("Failed to delete old channel post.") from exc
