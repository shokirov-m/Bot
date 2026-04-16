"""
Награды за победу: опыт, золото, шанс дропа (ТЗ 1.4).
"""

from __future__ import annotations

import random

from game.balance import (
    DROP_CHANCE_ELITE,
    DROP_CHANCE_FLOOR_LOW_MAX,
    DROP_CHANCE_MAJOR,
    DROP_CHANCE_MINI,
    DROP_CHANCE_MULT_FLOOR_6_PLUS,
    DROP_CHANCE_MULT_FLOORS_1_TO_5,
    DROP_CHANCE_NORMAL,
    GOLD_BASE_OFFSET,
    GOLD_ELITE_EXTRA_RANGE,
    GOLD_ELITE_MULT,
    GOLD_MAJOR_EXTRA_RANGE,
    GOLD_MAJOR_MULT,
    GOLD_MINI_EXTRA_RANGE,
    GOLD_MINI_MULT,
    GOLD_NORMAL_EXTRA_RANGE,
    GOLD_PER_FLOOR,
    RUNE_CHANCE_ELITE,
    RUNE_CHANCE_MAJOR,
    RUNE_CHANCE_MINI,
    RUNE_CHANCE_NORMAL,
    XP_BASE_OFFSET,
    XP_ELITE_MULT,
    XP_MAJOR_MULT,
    XP_MINI_MULT,
    XP_PER_FLOOR,
)
from game.floors.monsters import FloorMonsterSpawn


def gold_reward(floor_number: int, spawn: FloorMonsterSpawn) -> int:
    base = GOLD_BASE_OFFSET + floor_number * GOLD_PER_FLOOR
    if spawn.is_major_boss:
        lo, hi = GOLD_MAJOR_EXTRA_RANGE
        return base * GOLD_MAJOR_MULT + random.randint(lo, hi)
    if spawn.is_mini_boss:
        lo, hi = GOLD_MINI_EXTRA_RANGE
        return base * GOLD_MINI_MULT + random.randint(lo, hi)
    if spawn.is_elite:
        lo, hi = GOLD_ELITE_EXTRA_RANGE
        return int(base * GOLD_ELITE_MULT) + random.randint(lo, hi)
    lo, hi = GOLD_NORMAL_EXTRA_RANGE
    return base + random.randint(lo, hi)


def experience_reward(floor_number: int, spawn: FloorMonsterSpawn) -> int:
    base = XP_BASE_OFFSET + floor_number * XP_PER_FLOOR
    if spawn.is_major_boss:
        return base * XP_MAJOR_MULT
    if spawn.is_mini_boss:
        return base * XP_MINI_MULT
    if spawn.is_elite:
        return int(base * XP_ELITE_MULT)
    return base


def roll_rune_stone(spawn: FloorMonsterSpawn) -> bool:
    chance = RUNE_CHANCE_NORMAL
    if spawn.is_elite:
        chance = RUNE_CHANCE_ELITE
    if spawn.is_mini_boss:
        chance = RUNE_CHANCE_MINI
    if spawn.is_major_boss:
        chance = RUNE_CHANCE_MAJOR
    return random.random() < chance


def _scale_item_drop_chance_for_floor(base: float, floor_number: int) -> float:
    f = int(floor_number)
    if f <= int(DROP_CHANCE_FLOOR_LOW_MAX):
        return min(0.95, float(base) * float(DROP_CHANCE_MULT_FLOORS_1_TO_5))
    if f >= 6:
        return min(0.95, float(base) * float(DROP_CHANCE_MULT_FLOOR_6_PLUS))
    return min(0.95, float(base))


def roll_item_drop(spawn: FloorMonsterSpawn, floor_number: int) -> bool:
    chance = DROP_CHANCE_NORMAL
    if spawn.is_elite:
        chance = DROP_CHANCE_ELITE
    if spawn.is_mini_boss:
        chance = DROP_CHANCE_MINI
    if spawn.is_major_boss:
        chance = DROP_CHANCE_MAJOR
    chance = _scale_item_drop_chance_for_floor(chance, floor_number)
    return random.random() < chance
