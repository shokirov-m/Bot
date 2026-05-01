"""Запросы к персонажам."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models.character import Character
from game.economy import stamina as stamina_mod
from db.models.user import User
from services.meta_migration_service import apply_legacy_title_rank_migration


async def get_by_id(session: AsyncSession, character_id: int) -> Character | None:
    """Персонаж по PK characters.id."""
    result = await session.execute(select(Character).where(Character.id == character_id))
    char = result.scalar_one_or_none()
    if char is not None:
        apply_legacy_title_rank_migration(char)
        await stamina_mod.catch_up_stamina_for_character(session, char)
    return char


async def get_by_user_id(session: AsyncSession, user_id: int) -> Character | None:
    """Персонаж по внутреннему ID пользователя (users.id)."""
    result = await session.execute(
        select(Character).where(Character.user_id == user_id),
    )
    char = result.scalar_one_or_none()
    if char is not None:
        apply_legacy_title_rank_migration(char)
        await stamina_mod.catch_up_stamina_for_character(session, char)
    return char


async def get_by_user_id_with_user(
    session: AsyncSession,
    user_id: int,
) -> Character | None:
    """Персонаж с подгруженным user (для профиля)."""
    result = await session.execute(
        select(Character)
        .where(Character.user_id == user_id)
        .options(selectinload(Character.user)),
    )
    char = result.scalar_one_or_none()
    if char is not None:
        apply_legacy_title_rank_migration(char)
        await stamina_mod.catch_up_stamina_for_character(session, char)
    return char


async def count_characters(session: AsyncSession) -> int:
    r = await session.execute(select(func.count()).select_from(Character))
    return int(r.scalar_one() or 0)


async def list_characters_admin_browser(
    session: AsyncSession,
    *,
    offset: int,
    limit: int,
) -> list[tuple[int, str, int, int, bool, str]]:
    """
    Срез персонажей для админ-обзора: character_id, display_name, level, telegram_id, is_banned, class_key.
    """
    stmt = (
        select(
            Character.id,
            Character.display_name,
            Character.level,
            User.telegram_id,
            User.is_banned,
            Character.class_key,
        )
        .join(User, Character.user_id == User.id)
        .order_by(Character.id.asc())
        .offset(int(offset))
        .limit(int(limit))
    )
    r = await session.execute(stmt)
    rows = r.all()
    return [
        (int(row[0]), str(row[1]), int(row[2]), int(row[3]), bool(row[4]), str(row[5]))
        for row in rows
    ]


async def get_by_game_id(session: AsyncSession, game_id: int) -> Character | None:
    """Персонаж по публичному игровому ID (не забаненный пользователь)."""
    stmt = (
        select(Character)
        .join(User, Character.user_id == User.id)
        .where(Character.game_id == int(game_id), User.is_banned.is_(False))
    )
    result = await session.execute(stmt)
    char = result.scalar_one_or_none()
    if char is not None:
        apply_legacy_title_rank_migration(char)
        await stamina_mod.catch_up_stamina_for_character(session, char)
    return char


async def allocate_next_game_id(session: AsyncSession) -> int:
    """Следующий свободный game_id (max+1)."""
    r = await session.execute(select(func.coalesce(func.max(Character.game_id), 0)))
    return int(r.scalar_one() or 0) + 1


async def lock_character_row(session: AsyncSession, character_id: int) -> None:
    """
    Блокировка строки персонажа до конца транзакции (PostgreSQL: FOR UPDATE).
    Вызывать перед read-modify-write meta_progress при параллельных запросах.
    """
    await session.execute(select(Character.id).where(Character.id == character_id).with_for_update())


async def random_shadow_opponent(session: AsyncSession, exclude_character_id: int) -> Character | None:
    """Случайный персонаж для арены (не ты, не забанен)."""
    stmt = (
        select(Character)
        .join(User, Character.user_id == User.id)
        .where(
            and_(
                Character.id != exclude_character_id,
                User.is_banned.is_(False),
            ),
        )
        .order_by(func.random())
        .limit(1)
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none()


async def admin_dashboard_metrics(session: AsyncSession) -> dict[str, Any]:
    """Сводка для /admin stats (несколько агрегатов в одной сессии)."""
    start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)

    total_users = int(
        (await session.execute(select(func.count()).select_from(User))).scalar_one() or 0,
    )
    banned = int(
        (await session.execute(select(func.count()).where(User.is_banned.is_(True)))).scalar_one() or 0,
    )
    total_chars = int(
        (await session.execute(select(func.count()).select_from(Character))).scalar_one() or 0,
    )

    active_stmt = (
        select(func.count())
        .select_from(Character)
        .join(User, Character.user_id == User.id)
        .where(
            User.is_banned.is_(False),
            Character.updated_at >= start,
        )
    )
    active_today = int((await session.execute(active_stmt)).scalar_one() or 0)

    avg_stmt = (
        select(func.avg(Character.gold))
        .select_from(Character)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False))
    )
    avg_gold_f = (await session.execute(avg_stmt)).scalar_one()
    avg_gold = int(float(avg_gold_f or 0))

    top_stmt = (
        select(Character.display_name, Character.floor_number, User.username)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False))
        .order_by(Character.floor_number.desc(), Character.level.desc())
        .limit(1)
    )
    top_row = (await session.execute(top_stmt)).first()
    top_floor = int(top_row[1]) if top_row else 0
    top_name = str(top_row[0]) if top_row else "—"
    top_username = top_row[2] if top_row else None

    econ = await admin_economy_meta_aggregates(session)

    return {
        "total_users": total_users,
        "banned": banned,
        "total_chars": total_chars,
        "active_today": active_today,
        "avg_gold": avg_gold,
        "top_floor": top_floor,
        "top_display_name": top_name,
        "top_username": top_username,
        **econ,
    }


async def admin_economy_meta_aggregates(session: AsyncSession) -> dict[str, Any]:
    """
    Суммы по meta_progress (лотерея, долги, сейф) для /admin_stats.
    Обход персонажей не в бане; при очень большой базе можно заменить на JSON SQL.
    """
    from game.economy.sinks import META_BANK_SAFE_BALANCE, META_LOTTERY_SPENT, META_ML_DEBT

    stmt = (
        select(Character.meta_progress)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False))
    )
    rows = (await session.execute(stmt)).all()
    lottery_sum = 0
    safe_sum = 0
    safe_users = 0
    debtors = 0
    debt_sum = 0
    for (mp,) in rows:
        d = mp if isinstance(mp, dict) else {}
        lottery_sum += int(d.get(META_LOTTERY_SPENT) or 0)
        sb = int(d.get(META_BANK_SAFE_BALANCE) or 0)
        if sb > 0:
            safe_sum += sb
            safe_users += 1
        od = int(d.get(META_ML_DEBT) or 0)
        if od > 0:
            debtors += 1
            debt_sum += od
    return {
        "econ_lottery_spent_sum": lottery_sum,
        "econ_safe_gold_sum": safe_sum,
        "econ_safe_user_count": safe_users,
        "econ_debtor_count": debtors,
        "econ_debt_sum": debt_sum,
    }


async def count_bag_items(session: AsyncSession, character_id: int) -> int:
    from db.models.inventory import InventoryItem

    r = await session.execute(
        select(func.count()).where(
            InventoryItem.character_id == character_id,
            InventoryItem.bag_slot.isnot(None),
        ),
    )
    return int(r.scalar_one() or 0)
