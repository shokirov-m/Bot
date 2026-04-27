"""Топ персонажей: уровень, этаж, сумма статов, золото (без забаненных)."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.models.clan import Clan, ClanMembership
from db.models.user import User

DEFAULT_LIMIT = 10

_stat_sum = (
    Character.stat_strength
    + Character.stat_dexterity
    + Character.stat_intelligence
    + Character.stat_vitality
    + Character.stat_luck
)


async def top_by_level(session: AsyncSession, *, limit: int = DEFAULT_LIMIT) -> list[Character]:
    stmt = (
        select(Character)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False))
        .order_by(
            desc(Character.level),
            desc(Character.experience),
            desc(Character.floor_number),
        )
        .limit(limit)
    )
    r = await session.execute(stmt)
    return list(r.scalars().all())


async def top_by_floor(session: AsyncSession, *, limit: int = DEFAULT_LIMIT) -> list[Character]:
    """Топ по рекорду этажа: highest_floor_reached, не текущий floor_number."""
    stmt = (
        select(Character)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False))
        .order_by(
            desc(Character.highest_floor_reached),
            desc(Character.level),
            desc(Character.experience),
        )
        .limit(limit)
    )
    r = await session.execute(stmt)
    return list(r.scalars().all())


async def top_by_stat_sum(session: AsyncSession, *, limit: int = DEFAULT_LIMIT) -> list[Character]:
    stmt = (
        select(Character)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False))
        .order_by(desc(_stat_sum), desc(Character.level), desc(Character.floor_number))
        .limit(limit)
    )
    r = await session.execute(stmt)
    return list(r.scalars().all())


async def top_by_gold(session: AsyncSession, *, limit: int = DEFAULT_LIMIT) -> list[Character]:
    stmt = (
        select(Character)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False))
        .order_by(desc(Character.gold), desc(Character.level))
        .limit(limit)
    )
    r = await session.execute(stmt)
    return list(r.scalars().all())


async def get_clan_tags_for_characters(
    session: AsyncSession,
    character_ids: list[int],
) -> dict[int, str]:
    """
    Возвращает {character_id: clan_tag} для персонажей из списка.
    Если у персонажа нет клана или тег не задан — не включается в словарь.
    """
    if not character_ids:
        return {}
    stmt = (
        select(ClanMembership.character_id, Clan.tag)
        .join(Clan, ClanMembership.clan_id == Clan.id)
        .where(
            ClanMembership.character_id.in_(character_ids),
            Clan.tag.isnot(None),
            Clan.tag != "",
        )
    )
    result = await session.execute(stmt)
    return {int(row[0]): str(row[1]) for row in result.all()}


async def top_clans(session: AsyncSession, *, limit: int = 10) -> list[Clan]:
    stmt = (
        select(Clan)
        .order_by(
            desc(Clan.clan_level),
            desc(Clan.clan_xp),
            desc(Clan.created_at),
        )
        .limit(limit)
    )
    r = await session.execute(stmt)
    return list(r.scalars().all())


async def top_by_class(
    session: AsyncSession, class_key: str, *, limit: int = 10
) -> list[Character]:
    stmt = (
        select(Character)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False), Character.class_key == class_key)
        .order_by(desc(Character.level), desc(Character.experience))
        .limit(limit)
    )
    r = await session.execute(stmt)
    return list(r.scalars().all())


def character_total_stats(c: Character) -> int:
    return (
        int(c.stat_strength)
        + int(c.stat_dexterity)
        + int(c.stat_intelligence)
        + int(c.stat_vitality)
        + int(c.stat_luck)
    )
