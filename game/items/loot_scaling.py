"""
Скейлинг защиты и hp_bonus лута по номеру этажа (1..100).
Единая точка для баланса; таблицы дропа в loot.py вызывают эти функции.
"""

from __future__ import annotations


def _fl(floor_number: int) -> int:
    return max(1, min(100, int(floor_number)))


# --- Общие куски (обычный лут, fl <= 12) ---


def normal_gloves_defense(fl: int) -> int:
    f = _fl(fl)
    return max(1, 1 + f // 15)


def normal_ring_defense(fl: int) -> int:
    f = _fl(fl)
    return max(1, 1 + f // 20)


def normal_weapon_attack_low(fl: int, *, dagger_or_bow: bool) -> int:
    f = _fl(fl)
    return max(4, 4 + f // 3 + (1 if dagger_or_bow else 0))


def moss_armor_defense(fl: int) -> int:
    f = _fl(fl)
    return max(2, 2 + f // 8)


def moss_armor_hp_bonus(fl: int) -> int:
    f = _fl(fl)
    return max(5, 5 + f // 4)


def cap_defense(fl: int) -> int:
    f = _fl(fl)
    return max(1, 1 + f // 10)


def charm_defense(fl: int) -> int:
    f = _fl(fl)
    return max(1, 1 + f // 12)


def boots_defense(fl: int) -> int:
    f = _fl(fl)
    return max(1, 1 + f // 14)


def cloak_defense(fl: int) -> int:
    f = _fl(fl)
    return max(1, 1 + f // 16)


def rare_edge_attack(fl: int) -> int:
    f = _fl(fl)
    return max(7, 6 + f // 2)


def greatsword_attack(fl: int) -> int:
    """Двуручник под СИЛ: чуть выше обычного одноручного клинка."""
    f = _fl(fl)
    base = max(4, 4 + f // 3)
    return max(8, base + 2 + f // 5)


def balanced_shield_defense(fl: int) -> int:
    f = _fl(fl)
    return max(2, 2 + f // 10)


# --- Элита ---


def elite_weapon_attack(fl: int, *, staff_or_dagger: bool) -> int:
    f = _fl(fl)
    return max(6, 7 + f // 2 + (3 if staff_or_dagger else 0))


def elite_armor_defense_base(fl: int) -> int:
    f = _fl(fl)
    return max(2, 3 + f // 5)


def elite_armor_hp_bonus(fl: int) -> int:
    f = _fl(fl)
    return max(8, 6 + f // 3)


def elite_helm_defense(fl: int, defense_base: int) -> int:
    return max(1, defense_base // 2 + 1)


# --- Мини-босс ---


def mini_weapon_attack(fl: int) -> int:
    f = _fl(fl)
    return max(8, 10 + f // 2)


def mini_armor_defense(fl: int) -> int:
    f = _fl(fl)
    return max(4, 4 + f // 4)


def mini_armor_hp_bonus(fl: int) -> int:
    f = _fl(fl)
    return max(12, 10 + f // 5)


def mini_helm_defense(fl: int, defense: int) -> int:
    return max(2, defense // 2)


def mini_gloves_defense(fl: int, defense: int) -> int:
    return max(1, defense // 3)


def mini_weapon_enchant(fl: int) -> int:
    f = _fl(fl)
    return max(1, f // 40)


# --- Мажор-босс ---


def major_weapon_attack(fl: int) -> int:
    f = _fl(fl)
    return max(12, 12 + (f * 3) // 4)


def major_armor_defense(fl: int) -> int:
    f = _fl(fl)
    return max(5, 5 + f // 3)


def major_armor_hp_bonus(fl: int) -> int:
    f = _fl(fl)
    return max(18, 14 + f // 4)


def major_weapon_enchant(fl: int) -> int:
    f = _fl(fl)
    return max(1, f // 22)


def major_amulet_defense(fl: int, defense: int) -> int:
    return max(2, defense // 3 + 1)


def major_ring_defense(fl: int, defense: int) -> int:
    return max(2, defense // 4 + 2)
