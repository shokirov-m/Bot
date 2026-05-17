"""
Первые три героя, одолевшие главного босса 10-го этажа (зона 1–10): +3 свободных очка характеристик.

При первом запуске логики выполняется ретроспектива по floor_progress (уже победившие босса).
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.app_global import AppGlobal
from db.models.character import Character
from db.models.floor_progress import FloorProgress

PAYLOAD_ROOT = "floor10_major_pioneer_race"
META_AWARDED = "floor10_pioneer_stat_bonus"
MAX_WINNERS = 3
BONUS_POINTS = 3


def _race_root(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get(PAYLOAD_ROOT)
    return dict(raw) if isinstance(raw, dict) else {}


async def _ensure_app_row(session: AsyncSession) -> AppGlobal:
    row = await session.get(AppGlobal, 1)
    if row is None:
        row = AppGlobal(id=1, payload={})
        session.add(row)
        await session.flush()
    return row


async def ensure_retro_first_three(session: AsyncSession) -> None:
    """Один раз: по БД заполнить до трёх победителей и выдать бонус тем, кто уже убил босса 10."""
    row = await _ensure_app_row(session)
    payload = dict(row.payload or {})
    root = _race_root(payload)
    if root.get("retro_done"):
        return

    stmt = (
        select(FloorProgress.character_id, FloorProgress.updated_at)
        .where(
            FloorProgress.floor_number == 10,
            FloorProgress.boss_defeated.is_(True),
        )
        .order_by(FloorProgress.updated_at.asc())
    )
    rows = list((await session.execute(stmt)).all())

    seen: set[int] = set()
    winner_ids: list[int] = []
    for cid, _ in rows:
        cid = int(cid)
        if cid in seen:
            continue
        seen.add(cid)
        winner_ids.append(cid)
        if len(winner_ids) >= MAX_WINNERS:
            break

    root["winner_character_ids"] = winner_ids
    root["retro_done"] = True
    payload[PAYLOAD_ROOT] = root
    row.payload = payload

    for cid in winner_ids:
        char = await session.get(Character, cid)
        if char is None:
            continue
        mp = dict(char.meta_progress or {})
        if mp.get(META_AWARDED):
            continue
        mp[META_AWARDED] = 1
        char.meta_progress = mp
        char.unspent_stat_points = int(char.unspent_stat_points or 0) + BONUS_POINTS

    await session.flush()
    logger.info("floor10 pioneer retro: winners={}", winner_ids)


async def on_floor10_major_boss_victory(
    session: AsyncSession,
    character: Character,
    *,
    battle_floor: int,
    spawn: Any,
) -> str:
    """
    Вызвать после победы над главным боссом. Возвращает HTML-суффикс для окна победы или "".
    """
    if not getattr(spawn, "is_major_boss", False):
        return ""
    if int(battle_floor) != 10:
        return ""

    await ensure_retro_first_three(session)

    row = await _ensure_app_row(session)
    payload = dict(row.payload or {})
    root = _race_root(payload)
    winner_ids: list[int] = [int(x) for x in (root.get("winner_character_ids") or []) if int(x) > 0]

    mp = dict(character.meta_progress or {})
    if mp.get(META_AWARDED):
        return ""

    if int(character.id) in winner_ids:
        if not mp.get(META_AWARDED):
            mp[META_AWARDED] = 1
            character.meta_progress = mp
        return ""

    if len(winner_ids) >= MAX_WINNERS:
        return ""

    winner_ids.append(int(character.id))
    root["winner_character_ids"] = winner_ids
    payload[PAYLOAD_ROOT] = root
    row.payload = payload

    mp[META_AWARDED] = 1
    character.meta_progress = mp
    character.unspent_stat_points = int(character.unspent_stat_points or 0) + BONUS_POINTS
    await session.flush()

    return (
        f"\n🥇 <b>Пионер зоны 1–10!</b> Ты среди первых <b>{MAX_WINNERS}</b> героев, что повергли "
        f"<b>главного босса 10-го этажа</b>.\n"
        f"🎁 <b>+{BONUS_POINTS}</b> свободных очка характеристик — потрать в /stats."
    )
