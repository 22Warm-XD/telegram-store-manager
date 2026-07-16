import pytest

from app.services.store_settings_service import InvalidStoreColorError, StoreSettingsService


class DummySettings:
    background_color = "#505559"
    avatar_file_id = None
    cover_file_id = None


class DummyRepository:
    def __init__(self) -> None:
        self.settings = DummySettings()

    async def get(self, *, for_update: bool = False):
        return self.settings


class DummySession:
    async def commit(self) -> None:
        return None


@pytest.mark.asyncio
async def test_store_color_is_normalized() -> None:
    service = StoreSettingsService(session=DummySession(), repository=DummyRepository())
    settings = await service.set_background_color("aabbcc")
    assert settings.background_color == "#AABBCC"


@pytest.mark.asyncio
async def test_store_color_rejects_invalid_input() -> None:
    service = StoreSettingsService(session=DummySession(), repository=DummyRepository())
    with pytest.raises(InvalidStoreColorError):
        await service.set_background_color("FFFFF")
