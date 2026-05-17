"""
Реестр спец-механик этажа: единая точка для floor_service / combat / UI.

Единая точка входа для спец-механик этажа (room_clear, explore, wave, зоны, long_floor).
"""

from __future__ import annotations

import types
from typing import Callable

from db.models.character import Character
from game.enemies.floors.spawns import FloorMonsterSpawn
from game.tower.mechanics import long_floor as long_floor_mod
from game.tower.mechanics.explore import explore_floor
from game.tower.mechanics.explore import explore_floor_22
from game.tower.mechanics.explore import explore_floor_4
from game.tower.mechanics.room_clear import room_clear_floor
from game.tower.mechanics.room_clear import room_clear_floor_10
from game.tower.mechanics.room_clear import room_clear_floor_24
from game.tower.mechanics.room_clear import room_clear_floor_26
from game.tower.mechanics.room_clear import room_clear_floor_30
from game.tower.mechanics.room_clear import room_clear_floor_40
from game.tower.mechanics.wave import wave_floor
from game.tower.mechanics.wave import wave_floor_27
from game.tower.mechanics.explore.instances import BY_FLOOR as EXPLORE_BY_FLOOR
from game.tower.mechanics.explore.instances import mechanic_for_floor as explore_mechanic
from game.tower.mechanics.room_clear.instances import BY_FLOOR as ROOM_CLEAR_BY_FLOOR
from game.tower.mechanics.room_clear.instances import mechanic_for_floor as room_clear_mechanic
from game.tower.mechanics.wave.instances import BY_FLOOR as WAVE_BY_FLOOR
from game.tower.mechanics.wave.instances import mechanic_for_floor as wave_mechanic
from game.tower.mechanics.zones import forest_beginnings
from game.tower.mechanics.zones import rotten_swamps

# ── Room clear (зачистка комнат) ─────────────────────────────────────────────

_ROOM_CLEAR_MODULES: dict[int, types.ModuleType] = {
    room_clear_floor.ROOM_CLEAR_FLOOR: room_clear_floor,
    room_clear_floor_10.ROOM_CLEAR_FLOOR_10: room_clear_floor_10,
    room_clear_floor_24.ROOM_CLEAR_FLOOR_24: room_clear_floor_24,
    room_clear_floor_26.ROOM_CLEAR_FLOOR_26: room_clear_floor_26,
    room_clear_floor_30.ROOM_CLEAR_FLOOR_30: room_clear_floor_30,
    room_clear_floor_40.ROOM_CLEAR_FLOOR_40: room_clear_floor_40,
}

_ROOM_CLEAR_CHECKERS: dict[int, Callable[[int], bool]] = {
    5: room_clear_floor.is_room_clear_floor,
    10: room_clear_floor_10.is_room_clear_floor_10,
    24: room_clear_floor_24.is_room_clear_floor_24,
    26: room_clear_floor_26.is_room_clear_floor_26,
    30: room_clear_floor_30.is_room_clear_floor_30,
    40: room_clear_floor_40.is_room_clear_floor_40,
}


def room_clear_module(floor_number: int) -> types.ModuleType | None:
    return _ROOM_CLEAR_MODULES.get(int(floor_number))


def is_room_clear_floor(floor_number: int) -> bool:
    fn = _ROOM_CLEAR_CHECKERS.get(int(floor_number))
    return bool(fn and fn(int(floor_number)))


# ── Explore ───────────────────────────────────────────────────────────────────

_EXPLORE_MODULES: dict[int, types.ModuleType] = {
    explore_floor_4.EXPLORE_FLOOR_4: explore_floor_4,
    explore_floor.EXPLORE_FLOOR: explore_floor,
    explore_floor_22.EXPLORE_FLOOR_22: explore_floor_22,
}

_EXPLORE_CHECKERS: dict[int, Callable[[int], bool]] = {
    explore_floor_4.EXPLORE_FLOOR_4: explore_floor_4.is_explore_floor_4,
    explore_floor.EXPLORE_FLOOR: explore_floor.is_explore_floor,
    explore_floor_22.EXPLORE_FLOOR_22: explore_floor_22.is_explore_floor_22,
}


def explore_module(floor_number: int) -> types.ModuleType | None:
    return _EXPLORE_MODULES.get(int(floor_number))


def is_explore_floor(floor_number: int) -> bool:
    fn = _EXPLORE_CHECKERS.get(int(floor_number))
    return bool(fn and fn(int(floor_number)))


# ── Wave ──────────────────────────────────────────────────────────────────────

_WAVE_MODULES: dict[int, types.ModuleType] = {
    wave_floor.WAVE_FLOOR: wave_floor,
    wave_floor_27.WAVE_FLOOR_27: wave_floor_27,
}

_WAVE_CHECKERS: dict[int, Callable[[int], bool]] = {
    wave_floor.WAVE_FLOOR: wave_floor.is_wave_floor,
    wave_floor_27.WAVE_FLOOR_27: wave_floor_27.is_wave_floor_27,
}


def wave_module(floor_number: int) -> types.ModuleType | None:
    return _WAVE_MODULES.get(int(floor_number))


def is_wave_floor(floor_number: int) -> bool:
    fn = _WAVE_CHECKERS.get(int(floor_number))
    return bool(fn and fn(int(floor_number)))


def is_scenario_floor(floor_number: int) -> bool:
    """Этаж со спец-механикой (explore / room_clear / wave)."""
    n = int(floor_number)
    return is_explore_floor(n) or is_room_clear_floor(n) or is_wave_floor(n)


def tower_field_repair_allowed(floor_number: int) -> bool:
    """Полевая починка на сценарных этажах (комнаты, волны, исследования)."""
    n = int(floor_number)
    if is_explore_floor(n) or is_room_clear_floor(n):
        return True
    return is_wave_floor(n) and not is_room_clear_floor(n)


def spawns_for_tower_progress(
    character: Character, floor_number: int
) -> list[FloorMonsterSpawn]:
    """Слоты для учёта «все цели этажа» — на особых этажах возвращает слоты сценария."""
    from game.enemies.floors.spawns import build_spawns_for_floor

    n = int(floor_number)
    if n == long_floor_mod.PILOT_FLOOR and long_floor_mod.is_long_floor_scenario_active(character):
        return long_floor_mod.all_long_floor_spawns()

    em = explore_mechanic(n)
    if em is not None:
        return [em.spawn_boss]

    rm = room_clear_mechanic(n)
    if rm is not None:
        if n == 26:
            from game.mercenaries.shadow_market_meta import floor_26_shadow_cleared

            if floor_26_shadow_cleared(character):
                return []
        return rm.all_room_clear_spawns()

    wm = wave_mechanic(n)
    if wm is not None:
        return wm.all_spawns()

    return build_spawns_for_floor(n)


__all__ = [
    "EXPLORE_BY_FLOOR",
    "ROOM_CLEAR_BY_FLOOR",
    "WAVE_BY_FLOOR",
    "explore_floor",
    "explore_floor_4",
    "explore_floor_22",
    "explore_mechanic",
    "explore_module",
    "forest_beginnings",
    "is_explore_floor",
    "is_room_clear_floor",
    "is_wave_floor",
    "long_floor_mod",
    "room_clear_floor",
    "room_clear_floor_10",
    "room_clear_floor_24",
    "room_clear_floor_26",
    "room_clear_floor_30",
    "room_clear_floor_40",
    "room_clear_mechanic",
    "room_clear_module",
    "rotten_swamps",
    "spawns_for_tower_progress",
    "tower_field_repair_allowed",
    "is_scenario_floor",
    "wave_floor",
    "wave_floor_27",
    "wave_mechanic",
    "wave_module",
]
