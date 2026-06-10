from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import StoreSettings
from app.database.repositories.store_settings import StoreSettingsRepository

HEX_COLOR_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


class InvalidStoreColorError(ValueError):
    pass


class StoreSettingsService:
    def __init__(self, *, session: AsyncSession, repository: StoreSettingsRepository) -> None:
        self.session = session
        self.repository = repository

    async def get(self) -> StoreSettings:
        return await self.repository.get()

    async def set_background_color(self, value: str) -> StoreSettings:
        normalized = value.strip()
        if not HEX_COLOR_RE.fullmatch(normalized):
            raise InvalidStoreColorError
        if not normalized.startswith("#"):
            normalized = f"#{normalized}"
        settings = await self.repository.get(for_update=True)
        settings.background_color = normalized.upper()
        await self.session.commit()
        return settings

    async def set_avatar(self, file_id: str) -> StoreSettings:
        settings = await self.repository.get(for_update=True)
        settings.avatar_file_id = file_id
        await self.session.commit()
        return settings

    async def set_cover(self, file_id: str) -> StoreSettings:
        settings = await self.repository.get(for_update=True)
        settings.cover_file_id = file_id
        await self.session.commit()
        return settings
