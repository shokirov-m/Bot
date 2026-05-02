"""
Мировое событие «Золотой гоблин»: раз в несколько часов один «обычный» этаж в диапазоне 5–20
(без исследований, комнат, волнового сценария и этажей с мини-/мажор-боссом по правилам башни).

Первый победитель получает фиксированную награду (остальные — обычную с каталога).

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


def floor_accepts_golden_goblin_event(floor_number: int) -> bool:
    """
    Этаж, где гоблин может появиться у игрока: не исследование, не зачистка комнат,
    не волны «wv_*», не этаж сильного или мини-босса по сетке башни.
    """
    fl = int(floor_number)
    if fl < FLOOR_MIN or fl > FLOOR_MAX:
        return False
    from game.floors import explore_floor_4 as e4_mod
    from game.floors import explore_floor as e8_mod
    from game.floors import explore_floor_22 as e22_mod
    from game.floors import floor_data as fd_mod
    from game.floors import room_clear_floor as rc5_mod
    from game.floors import room_clear_floor_10 as rc10_mod
    from game.floors import room_clear_floor_24 as rc24_mod
    from game.floors import wave_floor as wv_mod

    if (
        e4_mod.is_explore_floor_4(fl)
        or e8_mod.is_explore_floor(fl)
        or e22_mod.is_explore_floor_22(fl)
    ):
        return False
    if (
        rc5_mod.is_room_clear_floor(fl)
        or rc10_mod.is_room_clear_floor_10(fl)
        or rc24_mod.is_room_clear_floor_24(fl)
    ):
        return False
    if wv_mod.is_wave_floor(fl):
        return False
    if fd_mod.is_major_boss_floor(fl) or fd_mod.is_mini_boss_floor(fl):
        return False
    return True


def _pick_random_event_floor() -> int:
    eligible = [n for n in range(FLOOR_MIN, FLOOR_MAX + 1) if floor_accepts_golden_goblin_event(n)]
    if not eligible:
        return 11
    return int(random.choice(eligible))


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


ESCAPE_TIMEOUT_SECONDS: int = 30 * 60  # 30 минут


async def ensure_initial_spawn(session: AsyncSession) -> tuple[bool, int | None, int | None]:
    """
    При первом запуске создаёт волну 1. Возвращает
    (created_new, floor_or_none, wave_or_none) для рассылки.
    """
    import time as _time
    row = await _ensure_row(session)
    base = _payload(row)
    if base.get("gg_wave") is not None:
        return False, None, None
    fl = _pick_random_event_floor()
    base["gg_wave"] = 1
    base["gg_floor"] = fl
    base["gg_claimed"] = False
    base["gg_spawned_at"] = _time.time()
    row.payload = base
    await session.flush()
    return True, fl, 1


async def roll_next_spawn(session: AsyncSession) -> tuple[int, int]:
    """Новая волна (планировщик): случайный этаж, сброс «убит». Возвращает (wave, floor)."""
    import time as _time
    row = await _ensure_row(session)
    base = _payload(row)
    wave = int(base.get("gg_wave", 0)) + 1
    fl = _pick_random_event_floor()
    base["gg_wave"] = wave
    base["gg_floor"] = fl
    base["gg_claimed"] = False
    base["gg_spawned_at"] = _time.time()
    row.payload = base
    await session.flush()
    return wave, fl


async def try_escape_if_timeout(session: AsyncSession) -> tuple[bool, int | None]:
    """
    Проверяет, не истёк ли таймаут побега (30 мин).
    Если гоблин ещё активен и не убит — помечает как сбежавшего.
    Возвращает (escaped, floor_number_or_none).
    """
    import time as _time
    row = await session.get(AppGlobal, 1)
    if row is None:
        return False, None
    base = _payload(row)
    if base.get("gg_claimed"):
        return False, None
    spawned_at = base.get("gg_spawned_at")
    if spawned_at is None:
        return False, None
    elapsed = _time.time() - float(spawned_at)
    if elapsed < ESCAPE_TIMEOUT_SECONDS:
        return False, None
    # Гоблин сбегает: помечаем как claimed (чтобы скрыть с этажа)
    fl = int(base.get("gg_floor") or 0)
    base["gg_claimed"] = True
    base["gg_escaped"] = True
    row.payload = base
    await session.flush()
    return True, fl


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
    gf = int(base.get("gg_floor") or 0)
    if gf != int(floor_number):
        return False
    return floor_accepts_golden_goblin_event(gf)


async def merge_spawns_if_active(
    session: AsyncSession,
    character: Character,
    spawns: list[FloorMonsterSpawn],
) -> list[FloorMonsterSpawn]:
    fl = int(character.floor_number)
    # Пилотный длинный этаж (15): свой UI и последовательность — без гоблина.
    if long_floor_mod.is_long_floor_active(character):
        return spawns
    if not floor_accepts_golden_goblin_event(fl):
        return spawns
    if not await is_active_on_floor(session, fl):
        return spawns
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
    if not floor_accepts_golden_goblin_event(int(floor_number)):
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
