"""Топ персонажей: уровень, этаж, сумма статов, золото (без забаненных)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.app_global import AppGlobal
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


async def top_by_coliseum(session: AsyncSession, *, limit: int = DEFAULT_LIMIT) -> list[Character]:
    """Топ по числу побеждённых бойцов колизея (без JSON-функций SQL — совместимо со всеми SQLite)."""
    from services import coliseum_service

    # Кэшируем срез, чтобы не тянуть всех персонажей на каждый показ экрана.
    # TTL небольшой: актуальность важнее, но повторы кликов должны быть быстрыми.
    ttl_s = 60
    now = datetime.now(UTC)
    row = await session.get(AppGlobal, 1)
    payload = dict(row.payload or {}) if row is not None else {}
    raw = payload.get("coliseum_lb_v1") or {}
    try:
        updated_at_s = str(raw.get("updated_at") or "")
        updated_at = datetime.fromisoformat(updated_at_s) if updated_at_s else None
    except Exception:
        updated_at = None
    cached = raw.get("character_ids")
    if (
        isinstance(cached, list)
        and cached
        and updated_at is not None
        and (now - updated_at).total_seconds() <= ttl_s
    ):
        ids = [int(x) for x in cached[: int(limit)] if str(x).isdigit()]
        if ids:
            r = await session.execute(
                select(Character)
                .join(User, Character.user_id == User.id)
                .where(User.is_banned.is_(False), Character.id.in_(ids)),
            )
            by_id = {int(c.id): c for c in r.scalars().all()}
            out = [by_id[i] for i in ids if i in by_id]
            if out:
                return out[: int(limit)]

    # Фолбэк: полный пересчёт (как раньше).
    stmt = (
        select(Character)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False))
    )
    r = await session.execute(stmt)
    chars = list(r.scalars().all())

    def _defeated_n(ch: Character) -> int:
        return coliseum_service.defeated_count_safe(ch)

    chars.sort(
        key=lambda c: (
            -_defeated_n(c),
            -int(c.level or 0),
            -max(int(c.highest_floor_reached or 0), int(c.floor_number or 0)),
        ),
    )
    cut = chars[: int(limit)]
    # Сохраняем кэш (id=1 создаётся в других сервисах; здесь — только если существует).
    try:
        if row is None:
            row = AppGlobal(id=1, payload={})
            session.add(row)
            await session.flush()
            payload = {}
        payload["coliseum_lb_v1"] = {
            "character_ids": [int(c.id) for c in cut],
            "updated_at": now.isoformat(timespec="seconds"),
        }
        row.payload = payload
        await session.flush()
    except Exception:
        # Кэш — оптимизация; не должен ломать топ.
        pass
    return cut


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
