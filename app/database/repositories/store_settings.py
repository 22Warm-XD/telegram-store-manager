from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import StoreSettings


class StoreSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, *, for_update: bool = False) -> StoreSettings:
        stmt = select(StoreSettings).where(StoreSettings.id == 1)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        settings = result.scalar_one_or_none()
        if settings is None:
            settings = StoreSettings(id=1)
            self.session.add(settings)
            await self.session.flush()
        return settings
