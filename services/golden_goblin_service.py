"""
Мировое событие «Золотой гоблин»: раз в несколько часов один этаж (5–20),
первый победитель получает фиксированную награду (остальные — обычную с каталога).

Состояние в AppGlobal(id=1).payload: gg_wave, gg_floor, gg_claimed.
"""

from __future__ import annotations

import random
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.app_global import AppGlobal
from db.models.character import Character
from game.data.monsters import MONSTER_TEMPLATE_META
from game.floors import long_floor as long_floor_mod
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

TEMPLATE_KEY = "golden_goblin"
SLOT_CODE = "gg"
FLOOR_MIN = 5
FLOOR_MAX = 20


def build_spawn() -> FloorMonsterSpawn:
    meta = MONSTER_TEMPLATE_META[TEMPLATE_KEY]
    tpl = MonsterTemplate(
        key=TEMPLATE_KEY,
        name=str(meta.get("display_name", "Золотой гоблин")),
        emoji=str(meta.get("emoji", "💰")),
        element=str(meta.get("element", "earth")),
        blurb=str(meta.get("blurb", "")),
    )
    return FloorMonsterSpawn(
        slot_code=SLOT_CODE,
        template=tpl,
        is_elite=False,
        is_mini_boss=False,
        is_major_boss=False,
    )


async def _ensure_row(session: AsyncSession) -> AppGlobal:
    row = await session.get(AppGlobal, 1)
    if row is None:
        row = AppGlobal(id=1, payload={})
        session.add(row)
        await session.flush()
    return row


def _payload(session_row: AppGlobal) -> dict[str, Any]:
    return dict(session_row.payload or {})


async def ensure_initial_spawn(session: AsyncSession) -> tuple[bool, int | None, int | None]:
    """
    При первом запуске создаёт волну 1. Возвращает
    (created_new, floor_or_none, wave_or_none) для рассылки.
    """
    row = await _ensure_row(session)
    base = _payload(row)
    if base.get("gg_wave") is not None:
        return False, None, None
    fl = random.randint(FLOOR_MIN, FLOOR_MAX)
    base["gg_wave"] = 1
    base["gg_floor"] = fl
    base["gg_claimed"] = False
    row.payload = base
    await session.flush()
    return True, fl, 1


async def roll_next_spawn(session: AsyncSession) -> tuple[int, int]:
    """Новая волна (планировщик): случайный этаж, сброс «убит». Возвращает (wave, floor)."""
    row = await _ensure_row(session)
    base = _payload(row)
    wave = int(base.get("gg_wave", 0)) + 1
    fl = random.randint(FLOOR_MIN, FLOOR_MAX)
    base["gg_wave"] = wave
    base["gg_floor"] = fl
    base["gg_claimed"] = False
    row.payload = base
    await session.flush()
    return wave, fl


async def current_wave(session: AsyncSession) -> int:
    row = await session.get(AppGlobal, 1)
    if row is None:
        return 0
    return int(dict(row.payload or {}).get("gg_wave") or 0)


async def is_active_on_floor(session: AsyncSession, floor_number: int) -> bool:
    row = await session.get(AppGlobal, 1)
    if row is None:
        return False
    base = dict(row.payload or {})
    if base.get("gg_claimed"):
        return False
    return int(base.get("gg_floor") or 0) == int(floor_number)


async def merge_spawns_if_active(
    session: AsyncSession,
    character: Character,
    spawns: list[FloorMonsterSpawn],
) -> list[FloorMonsterSpawn]:
    if long_floor_mod.is_long_floor_active(character):
        return spawns
    fl = int(character.floor_number)
    if fl < FLOOR_MIN or fl > FLOOR_MAX:
        return spawns
    if not await is_active_on_floor(session, fl):
        return spawns
    # У этажа 3 нет боёв на карте — но 3 не в диапазоне 5–20.
    return [build_spawn(), *spawns]


async def try_claim_first_blood(session: AsyncSession, expected_wave: int) -> bool:
    """Атомарно помечает награду как забранную, если волна совпала и ещё не claimed."""
    if expected_wave <= 0:
        return False
    row = await _ensure_row(session)
    base = _payload(row)
    if int(base.get("gg_wave") or 0) != int(expected_wave):
        return False
    if base.get("gg_claimed"):
        return False
    base["gg_claimed"] = True
    row.payload = base
    await session.flush()
    return True


async def html_banner_for_floor(session: AsyncSession, floor_number: int) -> str:
    """Строка для текста этажа (HTML), если событие активно на этом ярусе."""
    if int(floor_number) < FLOOR_MIN or int(floor_number) > FLOOR_MAX:
        return ""
    row = await session.get(AppGlobal, 1)
    if row is None:
        return ""
    base = dict(row.payload or {})
    if base.get("gg_claimed"):
        return ""
    if int(base.get("gg_floor") or 0) != int(floor_number):
        return ""
    return (
        "\n💰 <b>Золотой гоблин</b> на этом этаже! "
        "<i>Первый победитель: 1000–2000 💰 и 1000 опыта.</i>"
    )


async def html_banner_photo_caption(session: AsyncSession, floor_number: int) -> str:
    short = await html_banner_for_floor(session, floor_number)
    if not short:
        return ""
    return "\n💰 <b>Золотой гоблин</b> здесь — первый убийца: 1000–2000 💰, 1000 опыта."
