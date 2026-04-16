"""
Пакетное и атомарное восстановление стамины в БД (SQLAlchemy async).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models.character import Character


def _max_stamina() -> int:
    return max(1, int(settings.MAX_STAMINA))


def _regen_interval_seconds() -> int:
    return max(1, int(settings.STAMINA_REGEN_INTERVAL))


def compute_minutes_to_next_regen(
    *,
    stamina: int,
    last_regen_at: datetime | None,
    now: datetime | None = None,
) -> int:
    """
    Минуты до следующего +1 стамины по модели «последний тик + интервал».
    Если стамина полная — 0. Для тестов можно передать now.
    """
    if stamina >= _max_stamina():
        return 0
    now = now or datetime.now(UTC)
    last = last_regen_at
    if last is None:
        return max(1, (_regen_interval_seconds() + 59) // 60)
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    deadline = last + timedelta(seconds=_regen_interval_seconds())
    sec_left = (deadline - now).total_seconds()
    if sec_left <= 0:
        return 0
    return max(1, int((sec_left + 59) // 60))


async def regen_stamina_all(session: AsyncSession) -> int:
    """
    Batch UPDATE: всем, у кого stamina < MAX_STAMINA, +1 и last_stamina_regen_at = now.
    Один запрос, без цикла по строкам.
    """
    mx = _max_stamina()
    now = datetime.now(UTC)
    stmt = (
        update(Character)
        .where(Character.stamina < mx)
        .values(
            stamina=Character.stamina + 1,
            last_stamina_regen_at=now,
        )
    )
    res = await session.execute(stmt)
    return int(res.rowcount or 0)


async def spend_stamina(session: AsyncSession, character_id: int) -> bool:
    """
    Списать 1 стамину атомарно (UPDATE … WHERE stamina > 0).
    True если строка обновлена.
    """
    stmt = (
        update(Character)
        .where(Character.id == character_id, Character.stamina > 0)
        .values(stamina=Character.stamina - 1)
    )
    res = await session.execute(stmt)
    return int(res.rowcount or 0) > 0


async def minutes_to_next_regen(session: AsyncSession, character_id: int) -> int:
    """Сколько минут до следующего +1 стамины (по last_stamina_regen_at + интервал)."""
    stmt = select(Character.stamina, Character.last_stamina_regen_at).where(Character.id == character_id)
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        return 0
    st, last = int(row[0]), row[1]
    return compute_minutes_to_next_regen(stamina=st, last_regen_at=last)
