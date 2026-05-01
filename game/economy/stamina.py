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
    Batch UPDATE: всем, у кого stamina < MAX_STAMINA и прошло >= REGEN_INTERVAL с последнего тика, +1.
    Также обрезает stamina > MAX_STAMINA (после снижения лимита).
    """
    mx = _max_stamina()
    interval_s = _regen_interval_seconds()
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=interval_s)
    # Cap over-max values first
    await session.execute(
        update(Character)
        .where(Character.stamina > mx)
        .values(stamina=mx)
    )
    stmt = (
        update(Character)
        .where(
            Character.stamina < mx,
            # Only regen if enough time has passed (or never regenerated)
            (Character.last_stamina_regen_at == None) | (Character.last_stamina_regen_at <= cutoff),  # noqa: E711
        )
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
    Обновляет last_stamina_regen_at — от него считается следующее восстановление.
    True если строка обновлена.
    """
    now = datetime.now(UTC)
    stmt = (
        update(Character)
        .where(Character.id == character_id, Character.stamina > 0)
        .values(stamina=Character.stamina - 1, last_stamina_regen_at=now)
    )
    res = await session.execute(stmt)
    return int(res.rowcount or 0) > 0


# Ограничение «догоняния» стамины за один запрос (антивзлом и разумный офлайн).
_MAX_STAMINA_CATCH_UP_TICKS = 144


async def catch_up_stamina_for_character(session: AsyncSession, character: Character) -> None:
    """
    Начислить пропущенные тики стамины по интервалу REGEN (если бот простаивал или игрок долго не открывал игру).
    Не даёт больше MAX_STAMINA; число тиков за вызов ограничено.
    """
    mx = _max_stamina()
    st = int(character.stamina or 0)
    if st >= mx:
        return
    interval = float(_regen_interval_seconds())
    if interval <= 0:
        return
    now = datetime.now(UTC)
    last = character.last_stamina_regen_at
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    if last is None:
        anchor = character.created_at
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=UTC)
        last = anchor
    elapsed = (now - last).total_seconds()
    if elapsed < interval:
        return
    raw_ticks = int(elapsed // interval)
    gain = min(raw_ticks, mx - st, _MAX_STAMINA_CATCH_UP_TICKS)
    if gain <= 0:
        return
    character.stamina = min(mx, st + gain)
    character.last_stamina_regen_at = last + timedelta(seconds=gain * interval)


async def minutes_to_next_regen(session: AsyncSession, character_id: int) -> int:
    """Сколько минут до следующего +1 стамины (по last_stamina_regen_at + интервал)."""
    stmt = select(Character.stamina, Character.last_stamina_regen_at).where(Character.id == character_id)
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        return 0
    st, last = int(row[0]), row[1]
    return compute_minutes_to_next_regen(stamina=st, last_regen_at=last)
