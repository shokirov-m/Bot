"""
Кривая опыта (ТЗ 1.9): опыт для перехода на следующий уровень с учётом этажа (зона).
"""

from __future__ import annotations

from game.balance import (
    PROGRESSION_BASE_EXP,
    PROGRESSION_LEVEL1_XP_NEEDED,
    PROGRESSION_XP_NEED_DIVISOR_FROM_LEVEL_2,
    ZONE_MULTIPLIER_BY_MAX_FLOOR,
)


def zone_multiplier_for_floor(floor_number: int) -> float:
    """
    Множитель зоны по номеру текущего этажа персонажа.
    Диапазоны из ТЗ (этаж как прогресс башни).
    """
    if floor_number <= 0:
        return 1.0
    for max_floor, mult in ZONE_MULTIPLIER_BY_MAX_FLOOR:
        if floor_number <= max_floor:
            return mult
    return ZONE_MULTIPLIER_BY_MAX_FLOOR[-1][1]


def experience_needed_for_next_level(level: int, floor_number: int) -> int:
    """
    Сколько опыта нужно набрать на текущем уровне `level`, чтобы получить level+1.
    Используем N = level + 1 как «целевой» уровень в формуле ТЗ.
    На 1-м уровне порог на 100 ниже (быстрее первый ап).
    """
    if level < 1:
        level = 1
    if level == 1:
        return PROGRESSION_LEVEL1_XP_NEEDED
    n_next = level + 1
    mult = zone_multiplier_for_floor(floor_number)
    need = max(1, int(PROGRESSION_BASE_EXP * (n_next**2.2) * mult))
    # Со 2-го уровня порог сильно ниже базовой формулы (~¼); 1→2 по-прежнему фикс.
    if level >= 2:
        need = max(1, need // PROGRESSION_XP_NEED_DIVISOR_FROM_LEVEL_2)
    return need
