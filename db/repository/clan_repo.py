"""Запросы к кланам."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.clan import Clan, ClanMembership
from db.models.character import Character

# Опыт клана: уровень = 1 + floor(clan_xp / CLAN_XP_PER_LEVEL), не выше CLAN_MAX_LEVEL.
CLAN_XP_PER_LEVEL = 400
CLAN_MAX_LEVEL = 10


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


async def get_clan_by_name(session: AsyncSession, name: str) -> Clan | None:
    result = await session.execute(select(Clan).where(Clan.name == name.strip()))
    return result.scalar_one_or_none()


async def get_clan_by_tag(session: AsyncSession, tag: str) -> Clan | None:
    result = await session.execute(
        select(Clan).where(Clan.tag == tag.upper().strip())
    )
    return result.scalar_one_or_none()


async def count_members(session: AsyncSession, clan_id: int) -> int:
    result = await session.execute(
        select(ClanMembership).where(ClanMembership.clan_id == int(clan_id)),
    )
    return len(list(result.scalars().all()))


async def get_all_memberships(session: AsyncSession, clan_id: int) -> list[ClanMembership]:
    result = await session.execute(
        select(ClanMembership).where(ClanMembership.clan_id == int(clan_id))
    )
    return list(result.scalars().all())


async def get_members_with_characters(
    session: AsyncSession, clan_id: int
) -> list[tuple[ClanMembership, Character]]:
    """Все участники клана вместе с их персонажами."""
    result = await session.execute(
        select(ClanMembership, Character)
        .join(Character, Character.id == ClanMembership.character_id)
        .where(ClanMembership.clan_id == int(clan_id))
        .order_by(ClanMembership.contribution_points.desc())
    )
    return list(result.all())


async def create_clan(session: AsyncSession, *, name: str, tag: str | None, leader: Character) -> Clan:
    c = Clan(
        name=name.strip()[:64],
        tag=tag.upper().strip()[:5] if tag else None,
        leader_character_id=int(leader.id),
        clan_xp=0,
        clan_level=1,
        payload={},
    )
    session.add(c)
    await session.flush()
    m = ClanMembership(
        clan_id=int(c.id),
        character_id=int(leader.id),
        role="leader",
        contribution_points=0,
        joined_at=datetime.now(UTC),
        last_active_at=datetime.now(UTC),
    )
    session.add(m)
    await session.flush()
    return c


async def add_member(
    session: AsyncSession, *, clan_id: int, character: Character, role: str = "member"
) -> ClanMembership:
    m = ClanMembership(
        clan_id=int(clan_id),
        character_id=int(character.id),
        role=role,
        contribution_points=0,
        joined_at=datetime.now(UTC),
        last_active_at=datetime.now(UTC),
    )
    session.add(m)
    await session.flush()
    return m


async def remove_member(session: AsyncSession, membership: ClanMembership) -> None:
    await session.delete(membership)
    await session.flush()


async def add_clan_xp(session: AsyncSession, clan: Clan, delta: int) -> None:
    nx = max(0, int(clan.clan_xp) + int(delta))
    clan.clan_xp = nx
    # Уровень клана управляется вручную (через level_up), а не автоматически.
    await session.flush()


async def add_contribution(
    session: AsyncSession, membership: ClanMembership, delta: int
) -> None:
    membership.contribution_points = max(0, int(membership.contribution_points or 0) + int(delta))
    membership.last_active_at = datetime.now(UTC)
    await session.flush()


async def update_payload(session: AsyncSession, clan: Clan, payload: dict[str, Any]) -> None:
    clan.payload = payload
    await session.flush()


async def find_clans_for_war(
    session: AsyncSession, exclude_clan_id: int, limit: int = 5
) -> list[Clan]:
    """Топ-5 кланов (по уровню) для объявления войны, не считая текущего."""
    result = await session.execute(
        select(Clan)
        .where(Clan.id != int(exclude_clan_id))
        .order_by(Clan.clan_level.desc(), Clan.clan_xp.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
