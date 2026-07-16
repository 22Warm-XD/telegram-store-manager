from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from aiogram.exceptions import TelegramForbiddenError

from app.database.models import Product, ProductCategory, ProductPhoto
from app.services.product_broadcast_service import ProductBroadcastService


class FakeUsers:
    def __init__(self) -> None:
        self.calls = 0

    async def list_telegram_ids(self, *, after_id: int, limit: int):
        self.calls += 1
        return [(1, 101), (2, 202)] if self.calls == 1 else []


@pytest.mark.asyncio
async def test_broadcast_continues_after_one_delivery_failure(monkeypatch) -> None:
    product = Product(id=7, title="Test", size="M", condition="New", description=None, category=ProductCategory.CLOTHING, price=100)
    product.photos = [ProductPhoto(file_id="photo", sort_order=1)]
    bot = SimpleNamespace(send_photo=AsyncMock(side_effect=[TelegramForbiddenError(method=SimpleNamespace(), message="blocked"), None]))
    settings = SimpleNamespace(mini_app_url="https://example.test")
    service = ProductBroadcastService(bot=bot, settings=settings, users=FakeUsers())
    monkeypatch.setattr("app.services.product_broadcast_service.asyncio.sleep", AsyncMock())

    await service.broadcast_new_product(product)

    assert bot.send_photo.await_count == 2
