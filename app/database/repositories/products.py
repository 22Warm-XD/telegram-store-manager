from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import AdminActionLog, Product, ProductCategory, ProductPhoto, ProductSource, ProductStatus


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_product(
        self,
        *,
        title: str,
        size: str,
        condition: str,
        description: str | None,
        category: ProductCategory,
        price: int,
        photo_file_ids: list[str],
        source: ProductSource = ProductSource.BOT,
        channel_chat_id: int | None = None,
        channel_message_id: int | None = None,
        channel_media_group_message_ids: list[int] | None = None,
        raw_text: str | None = None,
        raw_caption: str | None = None,
        entities_json: list[dict] | None = None,
        caption_entities_json: list[dict] | None = None,
        html_text: str | None = None,
        html_caption: str | None = None,
    ) -> Product:
        product = Product(
            title=title,
            size=size,
            condition=condition,
            description=description,
            category=category,
            price=price,
            status=ProductStatus.ACTIVE,
            source=source,
            channel_chat_id=channel_chat_id,
            channel_message_id=channel_message_id,
            channel_media_group_message_ids=channel_media_group_message_ids,
            raw_text=raw_text,
            raw_caption=raw_caption,
            entities_json=entities_json,
            caption_entities_json=caption_entities_json,
            html_text=html_text,
            html_caption=html_caption,
        )
        unique_photo_file_ids = list(dict.fromkeys(photo_file_ids))
        product.photos = [
            ProductPhoto(file_id=file_id, sort_order=index)
            for index, file_id in enumerate(unique_photo_file_ids, start=1)
        ]
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product, attribute_names=["photos"])
        return product

    async def get_product(
        self,
        product_id: int,
        *,
        load_photos: bool = True,
        for_update: bool = False,
    ) -> Product | None:
        stmt = select(Product).where(Product.id == product_id)
        if load_photos:
            stmt = stmt.options(selectinload(Product.photos))
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_by_category(
        self,
        category: ProductCategory,
        *,
        page: int,
        page_size: int,
    ) -> list[Product]:
        stmt = (
            select(Product)
            .where(
                Product.category == category,
                Product.status == ProductStatus.ACTIVE,
            )
            .options(selectinload(Product.photos))
            .order_by(Product.created_at.desc(), Product.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_active_by_category(self, category: ProductCategory) -> int:
        stmt = select(func.count(Product.id)).where(
            Product.category == category,
            Product.status == ProductStatus.ACTIVE,
        )
        return int((await self.session.scalar(stmt)) or 0)

    async def list_products_by_status(
        self,
        status: ProductStatus,
        *,
        page: int,
        page_size: int,
        include_archived: bool = False,
    ) -> list[Product]:
        conditions = [Product.status == status]
        if status == ProductStatus.SOLD and not include_archived:
            conditions.append(Product.archived_at.is_(None))
        stmt = (
            select(Product)
            .where(*conditions)
            .options(selectinload(Product.photos))
            .order_by(Product.updated_at.desc(), Product.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_products_by_status(
        self,
        status: ProductStatus,
        *,
        include_archived: bool = False,
    ) -> int:
        conditions = [Product.status == status]
        if status == ProductStatus.SOLD and not include_archived:
            conditions.append(Product.archived_at.is_(None))
        stmt = select(func.count(Product.id)).where(*conditions)
        return int((await self.session.scalar(stmt)) or 0)

    async def set_channel_post_info(
        self,
        product: Product,
        *,
        channel_message_id: int,
        media_group_message_ids: list[int] | None,
        channel_chat_id: int | None = None,
    ) -> None:
        product.channel_message_id = channel_message_id
        if channel_chat_id is not None:
            product.channel_chat_id = channel_chat_id
        product.channel_media_group_message_ids = media_group_message_ids
        await self.session.flush()

    async def archive_product(self, product: Product) -> Product:
        product.archived_at = datetime.now(timezone.utc)
        await self.session.flush()
        return product

    async def replace_photos(self, product: Product, photo_file_ids: list[str]) -> None:
        product.photos.clear()
        product.photos.extend(
            ProductPhoto(file_id=file_id, sort_order=index)
            for index, file_id in enumerate(dict.fromkeys(photo_file_ids), start=1)
        )
        await self.session.flush()

    async def list_public_products(self) -> list[Product]:
        stmt = (
            select(Product)
            .where(
                Product.archived_at.is_(None),
                Product.status == ProductStatus.ACTIVE,
            )
            .options(selectinload(Product.photos))
            .order_by(Product.created_at.desc(), Product.id.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_public_product(self, product_id: int) -> Product | None:
        stmt = (
            select(Product)
            .where(
                Product.id == product_id,
                Product.archived_at.is_(None),
                Product.status == ProductStatus.ACTIVE,
            )
            .options(selectinload(Product.photos))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_products_by_ids(self, product_ids: list[int]) -> list[Product]:
        if not product_ids:
            return []
        stmt = (
            select(Product)
            .where(
                Product.id.in_(product_ids),
                Product.archived_at.is_(None),
                Product.status == ProductStatus.ACTIVE,
            )
            .options(selectinload(Product.photos))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_photo_by_id(self, photo_id: int) -> ProductPhoto | None:
        stmt = select(ProductPhoto).where(ProductPhoto.id == photo_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class AdminActionLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_log(self, *, admin_id: int, action: str, product_id: int | None = None) -> AdminActionLog:
        log_entry = AdminActionLog(admin_id=admin_id, action=action, product_id=product_id)
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry
