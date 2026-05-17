"""Сбор метрик, вызов anticheat.py, запись admin_log."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from aiogram import Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from admin.anticheat import (
    AnticheatAlert,
    check_damage_value,
    check_fight_speed,
    check_floor_progress,
    check_gold_gain,
    check_skill_damage_value,
)
from config import settings
from db.models.character import Character
from db.repository import admin_log_repo

_fight_times: dict[int, deque[float]] = defaultdict(lambda: deque(maxlen=48))
_gold_deltas: dict[int, deque[tuple[float, int]]] = defaultdict(lambda: deque(maxlen=500))
_floor_residence: dict[int, tuple[int, float]] = {}


async def _persist_and_notify(
    session: AsyncSession,
    *,
    character: Character,
    alert: AnticheatAlert,
    bot: Bot | None,
) -> None:
    await admin_log_repo.save_log(
        session,
        actor_telegram_id=0,
        target_user_id=int(character.user_id),
        action=f"anticheat_{alert.check_type}",
        severity=alert.severity,
        message=alert.description,
        payload=alert.to_payload(),
    )
    await session.flush()
    if bot is not None:
        from admin import alerts

        try:
            await alerts.send_alert_to_admins(bot, alert)
        except Exception:
            logger.exception("send_alert_to_admins")


async def record_fight_start(
    session: AsyncSession,
    character: Character,
    *,
    telegram_id: int,
    username: str | None,
    bot: Bot | None = None,
) -> None:
    if not settings.ANTICHEAT_ENABLED:
        return
    now = time.monotonic()
    dq = _fight_times[telegram_id]
    dq.append(now)
    while dq and now - dq[0] > 10.0:
        dq.popleft()
    n = len(dq)
    alert = check_fight_speed(
        n,
        telegram_id=telegram_id,
        username=username,
        floor=int(character.floor_number),
        level=int(character.level),
    )
    if alert is not None:
        await _persist_and_notify(session, character=character, alert=alert, bot=bot)


async def record_gold_gain(
    session: AsyncSession,
    character: Character,
    *,
    telegram_id: int,
    username: str | None,
    gold_delta: int,
    bot: Bot | None = None,
) -> None:
    if not settings.ANTICHEAT_ENABLED or gold_delta <= 0:
        return
    now = time.time()
    dq = _gold_deltas[telegram_id]
    dq.append((now, int(gold_delta)))
    while dq and now - dq[0][0] > 3600.0:
        dq.popleft()
    total = sum(d for _, d in dq)
    alert = check_gold_gain(
        total,
        telegram_id=telegram_id,
        username=username,
        floor=int(character.floor_number),
        level=int(character.level),
    )
    if alert is not None:
        await _persist_and_notify(session, character=character, alert=alert, bot=bot)


async def record_physical_damage(
    session: AsyncSession,
    character: Character,
    *,
    telegram_id: int,
    username: str | None,
    damage: int,
    strength: int,
    weapon_atk: int,
    bot: Bot | None = None,
) -> None:
    if not settings.ANTICHEAT_ENABLED or damage <= 0:
        return
    alert = check_damage_value(
        int(damage),
        strength=int(strength),
        weapon_atk=int(weapon_atk),
        telegram_id=telegram_id,
        username=username,
        floor=int(character.floor_number),
        level=int(character.level),
    )
    if alert is not None:
        await _persist_and_notify(session, character=character, alert=alert, bot=bot)


async def record_skill_damage(
    session: AsyncSession,
    character: Character,
    *,
    telegram_id: int,
    username: str | None,
    damage: int,
    skill_kind: str,
    skill_power: float,
    strength: int,
    intelligence: int,
    weapon_atk: int,
    bot: Bot | None = None,
) -> None:
    if not settings.ANTICHEAT_ENABLED or damage <= 0:
        return
    alert = check_skill_damage_value(
        int(damage),
        kind=str(skill_kind),
        strength=int(strength),
        intelligence=int(intelligence),
        weapon_atk=int(weapon_atk),
        skill_power=float(skill_power),
        telegram_id=telegram_id,
        username=username,
        floor=int(character.floor_number),
        level=int(character.level),
    )
    if alert is not None:
        await _persist_and_notify(session, character=character, alert=alert, bot=bot)


async def record_floor_change(
    session: AsyncSession,
    character: Character,
    *,
    telegram_id: int,
    username: str | None,
    old_floor: int,
    new_floor: int,
    bot: Bot | None = None,
) -> None:
    if not settings.ANTICHEAT_ENABLED:
        return
    now = time.monotonic()
    # Подъём только в рамках уже открытых этажей (напр. 20 → 5 → 6) давал ложные ALERT:
    # dt между переходами маленький, а «скорость этажей/мин» — большая. Проверяем только
    # движение вверх в этаж, который ещё не был отмечен как highest_floor_reached.
    hi = int(character.highest_floor_reached)
    if new_floor > old_floor and int(new_floor) > hi:
        rec = _floor_residence.get(telegram_id)
        if rec is not None:
            cur_f, t0 = rec
            if cur_f == old_floor:
                dt = max(now - t0, 1e-3)
                alert = check_floor_progress(
                    old_floor,
                    new_floor,
                    dt,
                    telegram_id=telegram_id,
                    username=username,
                    floor=new_floor,
                    level=int(character.level),
                )
                if alert is not None:
                    await _persist_and_notify(session, character=character, alert=alert, bot=bot)
    _floor_residence[telegram_id] = (new_floor, now)


async def log_admin_action(
    session: AsyncSession,
    *,
    actor_telegram_id: int,
    target_user_id: int | None,
    action: str,
    message: str | None,
    payload: dict[str, object],
) -> None:
    await admin_log_repo.save_log(
        session,
        actor_telegram_id=actor_telegram_id,
        target_user_id=target_user_id,
        action=action,
        severity="INFO",
        message=message,
        payload=payload,
    )
    await session.flush()
