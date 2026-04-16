"""Топ персонажей: уровень, этаж, сумма статов, золото (без забаненных)."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
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
    stmt = (
        select(Character)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False))
        .order_by(
            desc(Character.floor_number),
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


def character_total_stats(c: Character) -> int:
    return (
        int(c.stat_strength)
        + int(c.stat_dexterity)
        + int(c.stat_intelligence)
        + int(c.stat_vitality)
        + int(c.stat_luck)
    )
