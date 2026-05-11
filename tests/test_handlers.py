from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.handlers.admin.admin_panel import admin_panel_handler
from app.handlers.user.support import reviews_handler
from app.services import formatter


class DummyState:
    async def clear(self) -> None:
        return None


class DummyProductService:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    async def record_admin_action(self, *, admin_id: int, action: str, product_id=None) -> None:
        self.calls.append((admin_id, action))


def build_settings() -> Settings:
    return Settings(
        BOT_TOKEN="token",
        ADMIN_IDS="1,2",
        CHANNEL_ID=-1001234567890,
        SUPPORT_USERNAME="demo_support",
        SUPPORT_URL="https://t.me/demo_support",
        REVIEWS_URL="https://t.me/demo_reviews",
        TIKTOK_URL="https://example.com/tiktok",
        LOGISTICS_URL="https://t.me/demo_channel/1",
        POSTGRES_HOST="postgres",
        POSTGRES_PORT=5432,
        POSTGRES_DB="store_manager",
        POSTGRES_USER="store_manager",
        POSTGRES_PASSWORD="change_me",
        REDIS_HOST="redis",
        REDIS_PORT=6379,
        REDIS_DB=0,
        LOG_LEVEL="INFO",
    )


@pytest.mark.asyncio
async def test_admin_panel_denies_regular_user() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=999),
        answer=AsyncMock(),
    )
    service = DummyProductService()

    await admin_panel_handler(message, build_settings(), DummyState(), service)

    message.answer.assert_awaited_once_with(formatter.format_no_access_message())
    assert service.calls == []


@pytest.mark.asyncio
async def test_reviews_handler_sends_link_button() -> None:
    message = SimpleNamespace(answer=AsyncMock())
    settings = build_settings()

    await reviews_handler(message, settings)

    message.answer.assert_awaited_once()
    _, kwargs = message.answer.await_args
    assert kwargs["parse_mode"] == "HTML"
    assert kwargs["reply_markup"].inline_keyboard[0][0].url == settings.reviews_url
