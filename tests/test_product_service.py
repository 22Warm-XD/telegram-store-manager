from types import SimpleNamespace

import pytest

from app.database.models import Product, ProductCategory, ProductPhoto, ProductSource, ProductStatus
from app.services.exceptions import ChannelOperationError, InvalidPriceError, ProductAlreadySoldError
from app.services.product_service import ProductDraft, ProductService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, product, attribute_names=None) -> None:
        return None


class FakeProductsRepo:
    def __init__(self, product: Product | None = None) -> None:
        self.product = product
        self.created_product: Product | None = None
        self.set_channel_args = None

    async def create_product(self, **kwargs) -> Product:
        product = Product(
            id=1,
            title=kwargs["title"],
            size=kwargs["size"],
            condition=kwargs["condition"],
            description=kwargs["description"],
            category=kwargs["category"],
            price=kwargs["price"],
            status=ProductStatus.ACTIVE,
        )
        product.photos = [
            ProductPhoto(file_id=file_id, sort_order=index)
            for index, file_id in enumerate(kwargs["photo_file_ids"], start=1)
        ]
        self.created_product = product
        self.product = product
        return product

    async def set_channel_post_info(
        self,
        product: Product,
        *,
        channel_message_id: int,
        media_group_message_ids,
        channel_chat_id=None,
    ):
        product.channel_message_id = channel_message_id
        product.channel_media_group_message_ids = media_group_message_ids
        self.set_channel_args = (channel_message_id, media_group_message_ids)

    async def count_active_by_category(self, category: ProductCategory) -> int:
        return 0

    async def list_active_by_category(self, category: ProductCategory, *, page: int, page_size: int):
        return []

    async def count_products_by_status(self, status: ProductStatus, *, include_archived: bool = False) -> int:
        return 0

    async def list_products_by_status(self, status: ProductStatus, *, page: int, page_size: int, include_archived: bool = False):
        return []

    async def get_product(self, product_id: int, *, load_photos: bool = True, for_update: bool = False):
        return self.product

    async def archive_product(self, product: Product) -> Product:
        product.archived_at = "archived"
        return product


class FakeAdminLogsRepo:
    def __init__(self) -> None:
        self.entries: list[tuple[int, str, int | None]] = []

    async def add_log(self, *, admin_id: int, action: str, product_id: int | None = None):
        self.entries.append((admin_id, action, product_id))
        return SimpleNamespace(id=len(self.entries))


class FakeChannelService:
    def __init__(self) -> None:
        self.published_products: list[Product] = []
        self.edited_products: list[Product] = []
        self.discount_posts: list[Product] = []
        self.sold_products: list[Product] = []

    async def publish_product(self, product: Product):
        self.published_products.append(product)
        return SimpleNamespace(channel_message_id=555, media_group_message_ids=[555, 556], channel_chat_id=-1001)

    async def edit_product_post(self, product: Product) -> None:
        self.edited_products.append(product)
        return SimpleNamespace(
            channel_message_id=product.channel_message_id,
            media_group_message_ids=product.channel_media_group_message_ids,
            channel_chat_id=product.channel_chat_id,
        )

    async def mark_product_as_sold(self, product: Product) -> None:
        self.sold_products.append(product)
        return SimpleNamespace(
            channel_message_id=product.channel_message_id,
            media_group_message_ids=product.channel_media_group_message_ids,
            channel_chat_id=product.channel_chat_id,
        )


class FailingChannelService(FakeChannelService):
    async def edit_product_post(self, product: Product) -> None:
        raise ChannelOperationError("channel edit failed")

    async def mark_product_as_sold(self, product: Product) -> None:
        raise ChannelOperationError("channel edit failed")


def build_existing_product(*, status: ProductStatus = ProductStatus.ACTIVE, price: int = 21990) -> Product:
    product = Product(
        id=10,
        title="Nike Air Force 1 Mid OFF-WHITE",
        size="42 eur",
        condition="Новые 10/10",
        description=None,
        category=ProductCategory.SHOES,
        price=price,
        old_price=None,
        status=status,
        channel_message_id=100,
    )
    product.photos = [ProductPhoto(file_id="file-1", sort_order=1)]
    return product


def build_imported_product(*, status: ProductStatus = ProductStatus.ACTIVE, price: int = 21990) -> Product:
    product = build_existing_product(status=status, price=price)
    product.source = ProductSource.CHANNEL_IMPORT
    return product


@pytest.mark.asyncio
async def test_publish_product_persists_and_logs() -> None:
    session = FakeSession()
    products = FakeProductsRepo()
    logs = FakeAdminLogsRepo()
    channel = FakeChannelService()
    service = ProductService(session=session, products=products, admin_logs=logs, channel_service=channel)

    product = await service.publish_product(
        admin_id=123,
        draft=ProductDraft(
            title="Stone Island Hand Brushed",
            size="M",
            condition="9/10",
            description="0",
            category=ProductCategory.CLOTHING,
            price=17990,
            photo_file_ids=["file-1", "file-2"],
        ),
    )

    assert product.channel_message_id == 555
    assert product.channel_media_group_message_ids == [555, 556]
    assert session.commits == 1
    assert logs.entries[-1] == (123, "PUBLISH_PRODUCT", 1)


@pytest.mark.asyncio
async def test_publish_product_deduplicates_photo_file_ids() -> None:
    session = FakeSession()
    products = FakeProductsRepo()
    logs = FakeAdminLogsRepo()
    channel = FakeChannelService()
    service = ProductService(session=session, products=products, admin_logs=logs, channel_service=channel)

    product = await service.publish_product(
        admin_id=123,
        draft=ProductDraft(
            title="Stone Island Hand Brushed",
            size="M",
            condition="9/10",
            description="0",
            category=ProductCategory.CLOTHING,
            price=17990,
            photo_file_ids=["file-1", "file-1"],
        ),
    )

    assert [photo.file_id for photo in product.photos] == ["file-1"]
    assert [photo.file_id for photo in channel.published_products[0].photos] == ["file-1"]


@pytest.mark.asyncio
async def test_apply_discount_updates_price_and_edits_channel_post() -> None:
    session = FakeSession()
    products = FakeProductsRepo(product=build_existing_product())
    logs = FakeAdminLogsRepo()
    channel = FakeChannelService()
    service = ProductService(session=session, products=products, admin_logs=logs, channel_service=channel)

    product = await service.apply_discount(admin_id=123, product_id=10, new_price=19990)

    assert product.old_price == 21990
    assert product.price == 19990
    assert product.channel_message_id == 100
    assert product.channel_media_group_message_ids is None
    assert len(channel.edited_products) == 1
    assert logs.entries[-1] == (123, "APPLY_DISCOUNT", 10)


@pytest.mark.asyncio
async def test_apply_discount_rejects_sold_product() -> None:
    session = FakeSession()
    products = FakeProductsRepo(product=build_existing_product(status=ProductStatus.SOLD))
    logs = FakeAdminLogsRepo()
    channel = FakeChannelService()
    service = ProductService(session=session, products=products, admin_logs=logs, channel_service=channel)

    with pytest.raises(ProductAlreadySoldError):
        await service.apply_discount(admin_id=123, product_id=10, new_price=19990)

    assert logs.entries[-1] == (123, "APPLY_DISCOUNT_FAILED", 10)


@pytest.mark.asyncio
async def test_apply_discount_requires_lower_price() -> None:
    session = FakeSession()
    products = FakeProductsRepo(product=build_existing_product())
    logs = FakeAdminLogsRepo()
    channel = FakeChannelService()
    service = ProductService(session=session, products=products, admin_logs=logs, channel_service=channel)

    with pytest.raises(InvalidPriceError):
        await service.apply_discount(admin_id=123, product_id=10, new_price=21990)

    assert logs.entries[-1] == (123, "APPLY_DISCOUNT_FAILED", 10)


@pytest.mark.asyncio
async def test_remove_discount_restores_old_price_and_edits_channel_post() -> None:
    session = FakeSession()
    product = build_existing_product(price=19990)
    product.old_price = 21990
    products = FakeProductsRepo(product=product)
    logs = FakeAdminLogsRepo()
    channel = FakeChannelService()
    service = ProductService(session=session, products=products, admin_logs=logs, channel_service=channel)

    updated_product = await service.remove_discount(admin_id=123, product_id=10)

    assert updated_product.price == 21990
    assert updated_product.old_price is None
    assert len(channel.edited_products) == 1
    assert logs.entries[-1] == (123, "REMOVE_DISCOUNT", 10)


@pytest.mark.asyncio
async def test_mark_imported_product_as_sold_succeeds_when_channel_edit_fails() -> None:
    session = FakeSession()
    products = FakeProductsRepo(product=build_imported_product())
    logs = FakeAdminLogsRepo()
    channel = FailingChannelService()
    service = ProductService(session=session, products=products, admin_logs=logs, channel_service=channel)

    product = await service.mark_as_sold(admin_id=123, product_id=10)

    assert product.status == ProductStatus.SOLD
    assert session.commits == 1
    assert session.rollbacks == 0
    assert logs.entries[-1] == (123, "MARK_SOLD_CHANNEL_SYNC_FAILED", 10)
