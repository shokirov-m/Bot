"""
Награды за победу: опыт, золото, шанс дропа (ТЗ 1.4).
"""

from __future__ import annotations

import random

from game.balance import (
    DROP_CHANCE_ELITE_HIGH,
    DROP_CHANCE_ELITE_LOW,
    DROP_CHANCE_FLOOR_LOW_MAX,
    DROP_CHANCE_MAJOR_HIGH,
    DROP_CHANCE_MAJOR_LOW,
    DROP_CHANCE_MINI_HIGH,
    DROP_CHANCE_MINI_LOW,
    DROP_CHANCE_NORMAL_HIGH,
    DROP_CHANCE_NORMAL_LOW,
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
from game.enemies.floors.spawns import FloorMonsterSpawn


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
        g = int(base * GOLD_ELITE_MULT) + random.randint(lo, hi)
        bump = 1.28 + min(0.38, max(0, int(floor_number) - 8) * 0.02)
        return max(1, int(g * bump))
    lo, hi = GOLD_NORMAL_EXTRA_RANGE
    return base + random.randint(lo, hi)


def experience_reward(floor_number: int, spawn: FloorMonsterSpawn) -> int:
    base = XP_BASE_OFFSET + floor_number * XP_PER_FLOOR
    if spawn.is_major_boss:
        return base * XP_MAJOR_MULT
    if spawn.is_mini_boss:
        return base * XP_MINI_MULT
    if spawn.is_elite:
        x = int(base * XP_ELITE_MULT)
        bump = 1.2 + min(0.32, max(0, int(floor_number) - 8) * 0.018)
        return max(1, int(x * bump))
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


def luck_drop_bonus(stat_luck: int) -> float:
    """Бонус к шансу дропа от удачи: каждые 10 удачи = +1.5%, максимум +15% при 100+."""
    return min(0.15, (int(stat_luck) // 10) * 0.015)


def roll_item_drop(
    spawn: FloorMonsterSpawn,
    floor_number: int,
    stat_luck: int = 0,
    *,
    fame_loot_mult: float = 1.0,
) -> bool:
    is_low = int(floor_number) <= int(DROP_CHANCE_FLOOR_LOW_MAX)
    if spawn.is_major_boss:
        chance = DROP_CHANCE_MAJOR_LOW if is_low else DROP_CHANCE_MAJOR_HIGH
    elif spawn.is_mini_boss:
        chance = DROP_CHANCE_MINI_LOW if is_low else DROP_CHANCE_MINI_HIGH
    elif spawn.is_elite:
        chance = DROP_CHANCE_ELITE_LOW if is_low else DROP_CHANCE_ELITE_HIGH
    else:
        chance = DROP_CHANCE_NORMAL_LOW if is_low else DROP_CHANCE_NORMAL_HIGH
    chance += luck_drop_bonus(stat_luck)
    p = min(0.95, float(chance)) * max(0.0, float(fame_loot_mult))
    return random.random() < min(0.95, p)
