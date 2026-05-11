from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import PAGE_SIZE
from app.database.models import Product, ProductCategory, ProductSource, ProductStatus
from app.database.repositories.products import AdminActionLogRepository, ProductRepository
from app.services.channel_service import ChannelService
from app.services.exceptions import (
    ChannelOperationError,
    InvalidPriceError,
    InvalidProductStateError,
    ProductAlreadySoldError,
    ProductNotFoundError,
)


@dataclass(slots=True)
class ProductDraft:
    title: str
    size: str
    condition: str
    description: str | None
    category: ProductCategory
    price: int
    photo_file_ids: list[str]
    source: ProductSource = ProductSource.BOT
    channel_chat_id: int | None = None
    channel_message_id: int | None = None
    channel_media_group_message_ids: list[int] | None = None
    raw_text: str | None = None
    raw_caption: str | None = None
    entities_json: list[dict] | None = None
    caption_entities_json: list[dict] | None = None
    html_text: str | None = None
    html_caption: str | None = None


@dataclass(slots=True)
class PaginatedProducts:
    items: list[Product]
    page: int
    total_pages: int
    total_items: int


class ProductService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        products: ProductRepository,
        admin_logs: AdminActionLogRepository,
        channel_service: ChannelService,
    ) -> None:
        self.session = session
        self.products = products
        self.admin_logs = admin_logs
        self.channel_service = channel_service

    async def record_admin_action(self, *, admin_id: int, action: str, product_id: int | None = None) -> None:
        await self.admin_logs.add_log(admin_id=admin_id, action=action, product_id=product_id)
        await self.session.commit()

    async def list_catalog_products(
        self,
        *,
        category: ProductCategory,
        page: int,
        page_size: int = PAGE_SIZE,
    ) -> PaginatedProducts:
        total_items = await self.products.count_active_by_category(category)
        items = await self.products.list_active_by_category(category, page=page, page_size=page_size)
        total_pages = max(1, (total_items + page_size - 1) // page_size) if total_items else 1
        return PaginatedProducts(items=items, page=page, total_pages=total_pages, total_items=total_items)

    async def list_admin_products(
        self,
        *,
        status: ProductStatus,
        page: int,
        page_size: int = PAGE_SIZE,
    ) -> PaginatedProducts:
        total_items = await self.products.count_products_by_status(status)
        items = await self.products.list_products_by_status(status, page=page, page_size=page_size)
        total_pages = max(1, (total_items + page_size - 1) // page_size) if total_items else 1
        return PaginatedProducts(items=items, page=page, total_pages=total_pages, total_items=total_items)

    async def get_product(self, product_id: int, *, for_update: bool = False) -> Product:
        product = await self.products.get_product(product_id, for_update=for_update)
        if product is None:
            raise ProductNotFoundError
        return product

    async def publish_product(self, *, admin_id: int, draft: ProductDraft, publish_to_channel: bool = True) -> Product:
        self._validate_price(draft.price)
        photo_file_ids = self._dedupe_photo_file_ids(draft.photo_file_ids)
        if not photo_file_ids or len(photo_file_ids) > 5:
            raise InvalidProductStateError("Product must contain from 1 to 5 photos.")

        description = self._normalize_description(draft.description)
        try:
            product = await self.products.create_product(
                title=draft.title.strip(),
                size=draft.size.strip(),
                condition=draft.condition.strip(),
                description=description,
                category=draft.category,
                price=draft.price,
                photo_file_ids=photo_file_ids,
                source=draft.source,
                channel_chat_id=draft.channel_chat_id,
                channel_message_id=draft.channel_message_id,
                channel_media_group_message_ids=draft.channel_media_group_message_ids,
                raw_text=draft.raw_text,
                raw_caption=draft.raw_caption,
                entities_json=draft.entities_json,
                caption_entities_json=draft.caption_entities_json,
                html_text=draft.html_text,
                html_caption=draft.html_caption,
            )
            action = "ADD_PRODUCT_BOT_ONLY"
            if publish_to_channel:
                publish_result = await self.channel_service.publish_product(product)
                await self.products.set_channel_post_info(
                    product,
                    channel_message_id=publish_result.channel_message_id,
                    media_group_message_ids=publish_result.media_group_message_ids,
                    channel_chat_id=publish_result.channel_chat_id,
                )
                action = "PUBLISH_PRODUCT"
            elif draft.source == ProductSource.CHANNEL_IMPORT:
                action = "IMPORT_CHANNEL_PRODUCT"
            await self.admin_logs.add_log(admin_id=admin_id, action=action, product_id=product.id)
            await self.session.commit()
            await self.session.refresh(product, attribute_names=["photos"])
            return product
        except Exception as exc:
            await self.session.rollback()
            await self._record_failed_action(admin_id=admin_id, action="PUBLISH_PRODUCT_FAILED")
            if isinstance(exc, ChannelOperationError):
                raise
            raise

    async def apply_discount(self, *, admin_id: int, product_id: int, new_price: int) -> Product:
        self._validate_price(new_price)
        product = await self.products.get_product(product_id, for_update=True)
        if product is None:
            await self._record_failed_action(admin_id=admin_id, action="APPLY_DISCOUNT_FAILED", product_id=product_id)
            raise ProductNotFoundError
        if product.status == ProductStatus.SOLD:
            await self.session.rollback()
            await self._record_failed_action(admin_id=admin_id, action="APPLY_DISCOUNT_FAILED", product_id=product_id)
            raise ProductAlreadySoldError
        if new_price >= product.price:
            await self.session.rollback()
            await self._record_failed_action(admin_id=admin_id, action="APPLY_DISCOUNT_FAILED", product_id=product_id)
            raise InvalidPriceError

        previous_price = product.price
        previous_old_price = product.old_price
        previous_channel_message_id = product.channel_message_id
        previous_media_group_message_ids = product.channel_media_group_message_ids
        product.old_price = product.price
        product.price = new_price
        try:
            if product.channel_message_id is not None:
                publish_result = await self.channel_service.edit_product_post(product)
                await self.products.set_channel_post_info(
                    product,
                    channel_message_id=publish_result.channel_message_id,
                    media_group_message_ids=publish_result.media_group_message_ids,
                    channel_chat_id=publish_result.channel_chat_id,
                )
            await self.admin_logs.add_log(admin_id=admin_id, action="APPLY_DISCOUNT", product_id=product.id)
            await self.session.commit()
            return product
        except Exception as exc:
            if isinstance(exc, ChannelOperationError) and self._is_channel_sync_optional(product):
                await self.admin_logs.add_log(
                    admin_id=admin_id,
                    action="APPLY_DISCOUNT_CHANNEL_SYNC_FAILED",
                    product_id=product.id,
                )
                await self.session.commit()
                return product
            product.price = previous_price
            product.old_price = previous_old_price
            product.channel_message_id = previous_channel_message_id
            product.channel_media_group_message_ids = previous_media_group_message_ids
            await self.session.rollback()
            await self._record_failed_action(admin_id=admin_id, action="APPLY_DISCOUNT_FAILED", product_id=product_id)
            if isinstance(exc, ChannelOperationError):
                raise
            raise

    async def remove_discount(self, *, admin_id: int, product_id: int) -> Product:
        product = await self.products.get_product(product_id, for_update=True)
        if product is None:
            await self._record_failed_action(admin_id=admin_id, action="REMOVE_DISCOUNT_FAILED", product_id=product_id)
            raise ProductNotFoundError
        if product.status == ProductStatus.SOLD:
            await self.session.rollback()
            await self._record_failed_action(admin_id=admin_id, action="REMOVE_DISCOUNT_FAILED", product_id=product_id)
            raise ProductAlreadySoldError
        if product.old_price is None:
            await self.session.rollback()
            await self._record_failed_action(admin_id=admin_id, action="REMOVE_DISCOUNT_FAILED", product_id=product_id)
            raise InvalidPriceError

        discounted_price = product.price
        previous_price = product.old_price
        previous_channel_message_id = product.channel_message_id
        previous_media_group_message_ids = product.channel_media_group_message_ids
        product.price = product.old_price
        product.old_price = None
        try:
            if product.channel_message_id is not None:
                publish_result = await self.channel_service.edit_product_post(product)
                await self.products.set_channel_post_info(
                    product,
                    channel_message_id=publish_result.channel_message_id,
                    media_group_message_ids=publish_result.media_group_message_ids,
                    channel_chat_id=publish_result.channel_chat_id,
                )
            await self.admin_logs.add_log(admin_id=admin_id, action="REMOVE_DISCOUNT", product_id=product.id)
            await self.session.commit()
            return product
        except Exception as exc:
            if isinstance(exc, ChannelOperationError) and self._is_channel_sync_optional(product):
                await self.admin_logs.add_log(
                    admin_id=admin_id,
                    action="REMOVE_DISCOUNT_CHANNEL_SYNC_FAILED",
                    product_id=product.id,
                )
                await self.session.commit()
                return product
            product.price = discounted_price
            product.old_price = previous_price
            product.channel_message_id = previous_channel_message_id
            product.channel_media_group_message_ids = previous_media_group_message_ids
            await self.session.rollback()
            await self._record_failed_action(admin_id=admin_id, action="REMOVE_DISCOUNT_FAILED", product_id=product_id)
            if isinstance(exc, ChannelOperationError):
                raise
            raise

    async def mark_as_sold(self, *, admin_id: int, product_id: int) -> Product:
        product = await self.products.get_product(product_id, for_update=True)
        if product is None:
            await self._record_failed_action(admin_id=admin_id, action="MARK_SOLD_FAILED", product_id=product_id)
            raise ProductNotFoundError
        if product.status == ProductStatus.SOLD:
            await self.session.rollback()
            await self._record_failed_action(admin_id=admin_id, action="MARK_SOLD_FAILED", product_id=product_id)
            raise ProductAlreadySoldError

        product.status = ProductStatus.SOLD
        try:
            if product.channel_message_id is not None:
                publish_result = await self.channel_service.mark_product_as_sold(product)
                await self.products.set_channel_post_info(
                    product,
                    channel_message_id=publish_result.channel_message_id,
                    media_group_message_ids=publish_result.media_group_message_ids,
                    channel_chat_id=publish_result.channel_chat_id,
                )
            await self.admin_logs.add_log(admin_id=admin_id, action="MARK_SOLD", product_id=product.id)
            await self.session.commit()
            return product
        except Exception as exc:
            if isinstance(exc, ChannelOperationError) and self._is_channel_sync_optional(product):
                await self.admin_logs.add_log(
                    admin_id=admin_id,
                    action="MARK_SOLD_CHANNEL_SYNC_FAILED",
                    product_id=product.id,
                )
                await self.session.commit()
                return product
            await self.session.rollback()
            await self._record_failed_action(admin_id=admin_id, action="MARK_SOLD_FAILED", product_id=product_id)
            if isinstance(exc, ChannelOperationError):
                raise
            raise

    async def archive_sold_product(self, *, admin_id: int, product_id: int) -> Product:
        product = await self.products.get_product(product_id, for_update=True)
        if product is None:
            await self._record_failed_action(admin_id=admin_id, action="ARCHIVE_SOLD_FAILED", product_id=product_id)
            raise ProductNotFoundError
        if product.status != ProductStatus.SOLD:
            await self.session.rollback()
            await self._record_failed_action(admin_id=admin_id, action="ARCHIVE_SOLD_FAILED", product_id=product_id)
            raise InvalidProductStateError

        await self.products.archive_product(product)
        await self.admin_logs.add_log(admin_id=admin_id, action="ARCHIVE_SOLD", product_id=product.id)
        await self.session.commit()
        return product

    async def _record_failed_action(self, *, admin_id: int, action: str, product_id: int | None = None) -> None:
        await self.admin_logs.add_log(admin_id=admin_id, action=action, product_id=product_id)
        await self.session.commit()

    @staticmethod
    def _validate_price(price: int) -> None:
        if not isinstance(price, int) or price <= 0:
            raise InvalidPriceError

    @staticmethod
    def _normalize_description(description: str | None) -> str | None:
        if description is None:
            return None
        normalized = description.strip()
        if not normalized or normalized == "0":
            return None
        return normalized

    @staticmethod
    def _dedupe_photo_file_ids(photo_file_ids: list[str]) -> list[str]:
        unique_file_ids: list[str] = []
        seen_file_ids: set[str] = set()
        for file_id in photo_file_ids:
            if file_id in seen_file_ids:
                continue
            seen_file_ids.add(file_id)
            unique_file_ids.append(file_id)
        return unique_file_ids

    @staticmethod
    def _is_channel_sync_optional(product: Product) -> bool:
        return product.source == ProductSource.CHANNEL_IMPORT
