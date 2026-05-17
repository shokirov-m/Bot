"""
Формулы боя (ТЗ 1.4): урон, крит, уклонение, стихия.
"""

from __future__ import annotations

import math
import random

from game import balance as _bal


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def crit_chance_percent(luck: int, *, crit_bonus_flat: float = 0.0) -> float:
    """Крит: каждые 5 УДА = +1% (BALANCE_V2: шапка 50%; иначе 40%)."""
    base = (int(luck) // 5) * float(_bal.LUCK_CRIT_PER_5)
    cap = float(_bal.LUCK_CRIT_CAP) if _bal.BALANCE_V2_ENABLED else 0.40
    return clamp(base + crit_bonus_flat, 0.0, cap)


def dodge_chance_percent(dexterity: int, *, dodge_bonus_flat: float = 0.0) -> float:
    """Уклонение: каждые 5 ЛОВ = +1% (BALANCE_V2: шапка 45%; иначе 40%)."""
    base = (int(dexterity) // 5) * float(_bal.DEX_DODGE_PER_5)
    cap = float(_bal.DEX_DODGE_CAP) if _bal.BALANCE_V2_ENABLED else 0.40
    return clamp(base + dodge_bonus_flat, 0.0, cap)


def miss_chance_percent(dexterity: int, *, extra_miss_chance: float = 0.0) -> float:
    """
    Шанс промаха игрока: база 15%/20% (V2) − каждые 5 ЛОВ снимают 1%.
    Минимум 3% (нельзя полностью устранить промах).
    """
    base_v = float(_bal.DEX_MISS_BASE) if _bal.BALANCE_V2_ENABLED else 0.20
    base = base_v - (int(dexterity) // 5) * 0.01
    return clamp(base + float(extra_miss_chance), 0.03, max(0.20, base_v))


def roll_crit(luck: int, *, crit_bonus_flat: float = 0.0) -> bool:
    return random.random() < crit_chance_percent(luck, crit_bonus_flat=crit_bonus_flat)


def roll_dodge(dexterity: int, *, dodge_bonus_flat: float = 0.0) -> bool:
    return random.random() < dodge_chance_percent(dexterity, dodge_bonus_flat=dodge_bonus_flat)


def roll_miss(dexterity: int, *, extra_miss_chance: float = 0.0) -> bool:
    """Возвращает True, если атака игрока промахнулась."""
    return random.random() < miss_chance_percent(dexterity, extra_miss_chance=extra_miss_chance)


_ASSASSIN_CLASS_KEYS = frozenset({"scout", "assassin"})


def is_assassin_path_class(class_key: str | None) -> bool:
    return str(class_key or "").strip().lower() in _ASSASSIN_CLASS_KEYS


def min_dexterity_reaching_dodge_cap() -> int:
    """Минимальная ЛОВ, при которой вклад (d//5)*per достигает шапки уклонения (без gear-бонусов)."""
    cap = float(_bal.DEX_DODGE_CAP) if _bal.BALANCE_V2_ENABLED else 0.40
    per = float(_bal.DEX_DODGE_PER_5)
    chunks = max(0, int(math.ceil(cap / per - 1e-12)))
    return 5 * chunks


def dexterity_overflow_past_dodge_cap(dexterity: int) -> int:
    """
    Сколько пунктов ЛОВ «сверх» порога, после которого сырой уклон по ЛОВ не растёт.
    На пороге возвращает 0; первая лишняя ЛОВ даёт 1.
    """
    thr = min_dexterity_reaching_dodge_cap()
    return max(0, int(dexterity) - thr)


def assassin_accuracy_shred(dexterity: int, *, class_key: str | None) -> float:
    if not is_assassin_path_class(class_key):
        return 0.0
    ov = dexterity_overflow_past_dodge_cap(dexterity)
    raw = ov * float(_bal.ASSASSIN_ACCURACY_SHRED_PER_OVERFLOW_DEX)
    return min(float(_bal.ASSASSIN_ACCURACY_SHRED_CAP), raw)


def assassin_evasion_shred(dexterity: int, *, class_key: str | None) -> float:
    if not is_assassin_path_class(class_key):
        return 0.0
    ov = dexterity_overflow_past_dodge_cap(dexterity)
    raw = ov * float(_bal.ASSASSIN_EVASION_SHRED_PER_OVERFLOW_DEX)
    return min(float(_bal.ASSASSIN_EVASION_SHRED_CAP), raw)


def effective_monster_accuracy_on_player(
    monster_accuracy: float,
    dexterity: int,
    *,
    class_key: str | None,
) -> float:
    """Точность врага после «пробоя» убийцы (доля 0..1)."""
    acc = max(0.0, float(monster_accuracy))
    acc = max(0.0, acc - assassin_accuracy_shred(dexterity, class_key=class_key))
    return min(float(_bal.MONSTER_ACCURACY_CAP), acc)


def effective_dodge_chance_percent(
    dexterity: int,
    *,
    dodge_bonus_flat: float = 0.0,
    monster_accuracy: float = 0.0,
    class_key: str | None = None,
) -> float:
    """
    Уклонение игрока после вычета точности монстра (и учёта убийцы).
    Не выше «сырого» уклонения; не ниже DODGE_EFFECTIVE_MIN.
    """
    raw = dodge_chance_percent(dexterity, dodge_bonus_flat=dodge_bonus_flat)
    acc = effective_monster_accuracy_on_player(monster_accuracy, dexterity, class_key=class_key)
    eff = raw - acc
    eff = min(eff, raw)
    floor_m = float(_bal.DODGE_EFFECTIVE_MIN)
    if eff < floor_m:
        eff = min(floor_m, raw)
    return max(0.0, eff)


def roll_dodge_vs_monster(
    dexterity: int,
    *,
    dodge_bonus_flat: float = 0.0,
    monster_accuracy: float = 0.0,
    class_key: str | None = None,
) -> bool:
    return random.random() < effective_dodge_chance_percent(
        dexterity,
        dodge_bonus_flat=dodge_bonus_flat,
        monster_accuracy=monster_accuracy,
        class_key=class_key,
    )


def effective_monster_evasion_against_player(
    monster_evasion: float,
    dexterity: int,
    *,
    class_key: str | None,
) -> float:
    ev = max(0.0, float(monster_evasion))
    ev = max(0.0, ev - assassin_evasion_shred(dexterity, class_key=class_key))
    return min(float(_bal.MONSTER_EVASION_CAP), ev)


def miss_chance_percent_vs_monster(
    dexterity: int,
    *,
    extra_miss_chance: float = 0.0,
    monster_evasion: float = 0.0,
    class_key: str | None = None,
) -> float:
    """Промах по игроку с учётом уклонения врага (доля 0..1)."""
    base = miss_chance_percent(dexterity, extra_miss_chance=extra_miss_chance)
    ev = effective_monster_evasion_against_player(monster_evasion, dexterity, class_key=class_key)
    # Верхняя граница: не уносим шанс в невозможное; плюс уклонение врага.
    hi = max(0.92, float(_bal.DEX_MISS_BASE) if _bal.BALANCE_V2_ENABLED else 0.20)
    return clamp(base + ev, 0.03, hi)


def roll_miss_vs_monster(
    dexterity: int,
    *,
    extra_miss_chance: float = 0.0,
    monster_evasion: float = 0.0,
    class_key: str | None = None,
) -> bool:
    return random.random() < miss_chance_percent_vs_monster(
        dexterity,
        extra_miss_chance=extra_miss_chance,
        monster_evasion=monster_evasion,
        class_key=class_key,
    )


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
