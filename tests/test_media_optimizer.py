import asyncio
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from app.services.media_optimizer import MediaOptimizer, MediaVariant


def image_bytes(mode: str, size: tuple[int, int]) -> bytes:
    image = Image.new(mode, size, (255, 0, 0, 80) if "A" in mode else (255, 0, 0))
    output = io.BytesIO()
    image.save(output, "PNG" if "A" in mode else "JPEG")
    return output.getvalue()


def optimizer(tmp_path) -> MediaOptimizer:
    settings = SimpleNamespace(media_cache_dir=str(tmp_path), media_cache_max_mb=2048, bot_token="not-used")
    return MediaOptimizer(settings=settings, client=SimpleNamespace())


@pytest.mark.parametrize(("variant", "limit"), [(MediaVariant.CARD, 640), (MediaVariant.DETAIL, 1600), (MediaVariant.THUMB, 200)])
def test_webp_variants_are_bounded(variant, limit) -> None:
    content = MediaOptimizer._to_webp(image_bytes("RGB", (2000, 1200)), limit, 85)
    with Image.open(io.BytesIO(content)) as result:
        assert result.format == "WEBP"
        assert max(result.size) <= limit


def test_png_alpha_is_preserved() -> None:
    content = MediaOptimizer._to_webp(image_bytes("RGBA", (400, 400)), 640, 85)
    with Image.open(io.BytesIO(content)) as result:
        assert "A" in result.getbands()


def test_small_image_is_not_upscaled() -> None:
    content = MediaOptimizer._to_webp(image_bytes("RGB", (100, 60)), 640, 85)
    with Image.open(io.BytesIO(content)) as result:
        assert result.size == (100, 60)


@pytest.mark.asyncio
async def test_second_request_uses_cache_and_parallel_requests_share_work(tmp_path) -> None:
    service = optimizer(tmp_path)
    service._source = AsyncMock(return_value=image_bytes("RGB", (1000, 700)))
    await asyncio.gather(
        service.get_product("file-id", 1, MediaVariant.CARD),
        service.get_product("file-id", 1, MediaVariant.CARD),
    )
    await service.get_product("file-id", 1, MediaVariant.CARD)
    assert service._source.await_count == 1


@pytest.mark.asyncio
async def test_variants_have_distinct_cache_entries(tmp_path) -> None:
    service = optimizer(tmp_path)
    service._source = AsyncMock(return_value=image_bytes("RGB", (1000, 700)))
    card = await service.get_product("file-id", 1, MediaVariant.CARD)
    detail = await service.get_product("file-id", 1, MediaVariant.DETAIL)
    assert card.etag != detail.etag


@pytest.mark.asyncio
async def test_broken_image_falls_back_without_crashing(tmp_path) -> None:
    service = optimizer(tmp_path)
    service._source = AsyncMock(return_value=b"not an image")
    asset = await service.get_product("file-id", 1, MediaVariant.CARD)
    assert asset.content == b"not an image"
