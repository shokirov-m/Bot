"""
Формулы боя (ТЗ 1.4): урон, крит, уклонение, стихия.
"""

from __future__ import annotations

import random


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def crit_chance_percent(luck: int, *, crit_bonus_flat: float = 0.0) -> float:
    """Крит: каждые 5 УДА = +1%, макс 40%. crit_bonus_flat — плоская добавка в долях."""
    base = (int(luck) // 5) * 0.01
    return clamp(base + crit_bonus_flat, 0.0, 0.40)


def dodge_chance_percent(dexterity: int, *, dodge_bonus_flat: float = 0.0) -> float:
    """Уклонение: каждые 5 ЛОВ = +1%, макс 40%."""
    base = (int(dexterity) // 5) * 0.01
    return clamp(base + dodge_bonus_flat, 0.0, 0.40)


def miss_chance_percent(dexterity: int) -> float:
    """
    Шанс промаха игрока: база 20% − каждые 5 ЛОВ снимают 1%.
    Минимум 3% (нельзя полностью устранить промах), максимум 20%.
    Например: ЛОВ 0 → 20%, ЛОВ 25 → 15%, ЛОВ 50 → 10%, ЛОВ 85 → 3%.
    """
    base = 0.20 - (int(dexterity) // 5) * 0.01
    return clamp(base, 0.03, 0.20)


def roll_crit(luck: int, *, crit_bonus_flat: float = 0.0) -> bool:
    return random.random() < crit_chance_percent(luck, crit_bonus_flat=crit_bonus_flat)


def roll_dodge(dexterity: int, *, dodge_bonus_flat: float = 0.0) -> bool:
    return random.random() < dodge_chance_percent(dexterity, dodge_bonus_flat=dodge_bonus_flat)


def roll_miss(dexterity: int) -> bool:
    """Возвращает True, если атака игрока промахнулась."""
    return random.random() < miss_chance_percent(dexterity)


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


def physical_damage_split(
    strength: int,
    weapon_attack: int,
    enemy_defense: int,
    *,
    elemental_bonus_percent: int = 0,
    roll: float | None = None,
) -> tuple[int, int, int]:
    """
    Один бросок 0.85–1.15: (урон со стих. бонусом, урон без него, разница = вклад % рун).
    """
    r = float(roll) if roll is not None else random.uniform(0.85, 1.15)
    raw_base = strength * 2 + weapon_attack
    base_ne = raw_base
    base_yes = int(raw_base * (1 + elemental_bonus_percent / 100.0)) if elemental_bonus_percent else raw_base
    d_ne = max(1, int(base_ne * r) - enemy_defense)
    d_yes = max(1, int(base_yes * r) - enemy_defense)
    return d_yes, d_ne, max(0, d_yes - d_ne)


def physical_damage(
    strength: int,
    weapon_attack: int,
    enemy_defense: int,
    *,
    elemental_bonus_percent: int = 0,
    roll: float | None = None,
) -> int:
    """
    урон = (СИЛ*2 + оружие + элем_бонус%) * rand(0.85..1.15) - защита_врага
    elemental_bonus_percent — целые проценты (+15 => *1.15 к базе до вычитания защиты).
    """
    d_yes, _, _ = physical_damage_split(
        strength,
        weapon_attack,
        enemy_defense,
        elemental_bonus_percent=elemental_bonus_percent,
        roll=roll,
    )
    return d_yes


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
