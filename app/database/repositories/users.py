from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_user(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
    ) -> User:
        stmt = (
            insert(User)
            .values(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            .on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={
                    "username": username,
                    "first_name": first_name,
                },
            )
            .returning(User)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_telegram_ids(self, *, after_id: int = 0, limit: int = 100) -> list[tuple[int, int]]:
        stmt = select(User.id, User.telegram_id).where(User.id > after_id).order_by(User.id).limit(limit)
        return [(int(row.id), int(row.telegram_id)) for row in (await self.session.execute(stmt)).all()]
