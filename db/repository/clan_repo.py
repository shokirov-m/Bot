"""Запросы к кланам."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.clan import Clan, ClanMembership
from db.models.character import Character


async def get_membership(session: AsyncSession, character_id: int) -> ClanMembership | None:
    result = await session.execute(
        select(ClanMembership).where(ClanMembership.character_id == int(character_id)),
    )
    return result.scalar_one_or_none()


async def get_clan(session: AsyncSession, clan_id: int) -> Clan | None:
    result = await session.execute(select(Clan).where(Clan.id == int(clan_id)))
    return result.scalar_one_or_none()


async def count_members(session: AsyncSession, clan_id: int) -> int:
    result = await session.execute(
        select(ClanMembership).where(ClanMembership.clan_id == int(clan_id)),
    )
    return len(list(result.scalars().all()))


async def create_clan(session: AsyncSession, *, name: str, leader: Character) -> Clan:
    c = Clan(
        name=name.strip()[:64],
        leader_character_id=int(leader.id),
        clan_xp=0,
        clan_level=1,
    )
    session.add(c)
    await session.flush()
    m = ClanMembership(clan_id=int(c.id), character_id=int(leader.id), role="leader")
    session.add(m)
    await session.flush()
    return c


async def add_member(session: AsyncSession, *, clan_id: int, character: Character) -> ClanMembership:
    m = ClanMembership(clan_id=int(clan_id), character_id=int(character.id), role="member")
    session.add(m)
    await session.flush()
    return m


async def add_clan_xp(session: AsyncSession, clan: Clan, delta: int) -> None:
    nx = max(0, int(clan.clan_xp) + int(delta))
    clan.clan_xp = nx
    clan.clan_level = max(1, 1 + nx // 400)
    await session.flush()
