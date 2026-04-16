"""Запросы к кланам."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.clan import Clan, ClanMembership
from db.models.character import Character

# Опыт клана: уровень = 1 + floor(clan_xp / CLAN_XP_PER_LEVEL), не выше CLAN_MAX_LEVEL.
CLAN_XP_PER_LEVEL = 400
CLAN_MAX_LEVEL = 99


def clan_level_from_total_xp(total_xp: int) -> int:
    x = max(0, int(total_xp))
    raw = 1 + x // CLAN_XP_PER_LEVEL
    return min(CLAN_MAX_LEVEL, max(1, raw))


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
    clan.clan_level = clan_level_from_total_xp(nx)
    await session.flush()
