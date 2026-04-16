"""
Формулы боя (ТЗ 1.4): урон, крит, уклонение, стихия.
"""

from __future__ import annotations

import random


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def crit_chance_percent(luck: int, *, crit_bonus_flat: float = 0.0) -> float:
    """Крит: УДА * 0.5%, макс 50%. crit_bonus_flat — доля (0.2 = +20 п.п. к базе в долях — упрощаем как +к шансу)."""
    base = luck * 0.5 / 100.0
    base = clamp(base + crit_bonus_flat, 0.0, 0.50)
    return base


def dodge_chance_percent(dexterity: int, *, dodge_bonus_flat: float = 0.0) -> float:
    """Уклонение: ЛОВ * 0.4%, макс 40%."""
    base = dexterity * 0.4 / 100.0
    return clamp(base + dodge_bonus_flat, 0.0, 0.40)


def roll_crit(luck: int, *, crit_bonus_flat: float = 0.0) -> bool:
    return random.random() < crit_chance_percent(luck, crit_bonus_flat=crit_bonus_flat)


def roll_dodge(dexterity: int, *, dodge_bonus_flat: float = 0.0) -> bool:
    return random.random() < dodge_chance_percent(dexterity, dodge_bonus_flat=dodge_bonus_flat)


def int_skill_phys_tuning_multiplier(intelligence: int) -> float:
    """Физические навыки: ИНТ немного усиливает технику удара (все классы)."""
    return 1.0 + min(0.11, max(0.0, float(intelligence)) * 0.0020)


def int_skill_mag_extra_scale(intelligence: int) -> float:
    """Магические навыки: лёгкий доп. масштаб от ИНТ поверх базы magical_damage."""
    return 1.0 + min(0.07, max(0.0, float(intelligence)) * 0.0014)


def physical_damage_range(
    strength: int,
    weapon_attack: int,
    enemy_defense: int = 0,
    *,
    elemental_bonus_percent: int = 0,
) -> tuple[int, int]:
    """
    Диапазон физического урона без крита (коэфф. 0.85–1.15), для профиля / подсказок.
    """
    base = strength * 2 + weapon_attack
    if elemental_bonus_percent:
        base = int(base * (1 + elemental_bonus_percent / 100.0))
    lo = max(1, int(base * 0.85) - enemy_defense)
    hi = max(1, int(base * 1.15) - enemy_defense)
    return lo, hi


def physical_damage(
    strength: int,
    weapon_attack: int,
    enemy_defense: int,
    *,
    elemental_bonus_percent: int = 0,
) -> int:
    """
    урон = (СИЛ*2 + оружие + элем_бонус%) * rand(0.85..1.15) - защита_врага
    elemental_bonus_percent — целые проценты (+15 => *1.15 к базе до вычитания защиты).
    """
    base = strength * 2 + weapon_attack
    if elemental_bonus_percent:
        base = int(base * (1 + elemental_bonus_percent / 100.0))
    rolled = base * random.uniform(0.85, 1.15)
    dmg = int(rolled) - enemy_defense
    return max(1, dmg)


def magical_damage(
    intelligence: int,
    weapon_or_focus: int,
    enemy_defense: int,
    *,
    mag_bonus_percent: int = 0,
    elemental_bonus_percent: int = 0,
) -> int:
    """Магический урон: усиленная доля ИНТ + фокус, те же колебания."""
    int_core = intelligence * 2 + max(0, intelligence // 5)
    base = int_core + weapon_or_focus
    if mag_bonus_percent:
        base = int(base * (1 + mag_bonus_percent / 100.0))
    if elemental_bonus_percent:
        base = int(base * (1 + elemental_bonus_percent / 100.0))
    rolled = base * random.uniform(0.85, 1.15)
    dmg = int(rolled) - max(0, enemy_defense // 2)
    return max(1, dmg)


def crit_multiplier() -> float:
    return 1.75


def escape_chance(dexterity: int) -> float:
    """База 60% + бонус от ЛОВ, потолок 90%."""
    return clamp(0.60 + dexterity / 200.0, 0.60, 0.90)
