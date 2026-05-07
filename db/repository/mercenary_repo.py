from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.mercenary import Mercenary


async def count_for_character(session: AsyncSession, character_id: int) -> int:
    r = await session.scalar(
        select(func.count()).select_from(Mercenary).where(Mercenary.character_id == int(character_id)),
    )
    return int(r or 0)


async def list_for_character(session: AsyncSession, character_id: int) -> list[Mercenary]:
    res = await session.scalars(
        select(Mercenary).where(Mercenary.character_id == int(character_id)).order_by(Mercenary.id),
    )
    return list(res.all())


async def get_by_id(session: AsyncSession, mercenary_id: int) -> Mercenary | None:
    return await session.get(Mercenary, int(mercenary_id))


async def get_by_ids_for_character(
    session: AsyncSession,
    character_id: int,
    ids: list[int],
) -> list[Mercenary]:
    if not ids:
        return []
    res = await session.scalars(
        select(Mercenary).where(
            Mercenary.character_id == int(character_id),
            Mercenary.id.in_([int(x) for x in ids]),
        ),
    )
    return list(res.all())
