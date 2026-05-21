"""
Единая формула статов монстров (бывший «не-каталог» путь из combat_service).
Используется боем и генерацией реестра monster_registry.py.
"""

from __future__ import annotations

from typing import Any

from game.balance import (
    MONSTER_ACCURACY_CAP,
    MONSTER_ACCURACY_ELITE_ADD,
    MONSTER_ACCURACY_MAJOR_ADD,
    MONSTER_ACCURACY_MINI_ADD,
    MONSTER_ACCURACY_PER_FLOOR_AFTER_5,
    MONSTER_ATK_CURVE_MULT,
    MONSTER_ATK_FLAT_ELITE,
    MONSTER_ATK_FLAT_NORMAL,
    MONSTER_ATK_RAW_BASE,
    MONSTER_ATK_RAW_DIV_FLOOR,
    MONSTER_DEF_BASE,
    MONSTER_DEF_CURVE_MULT,
    MONSTER_DEF_DIV_FLOOR,
    MONSTER_EVASION_CAP,
    MONSTER_EVASION_ELITE_ADD,
    MONSTER_EVASION_MAJOR_ADD,
    MONSTER_EVASION_MINI_ADD,
    MONSTER_EVASION_PER_FLOOR_AFTER_5,
    MONSTER_FLOOR_DEF_PER_LEVEL,
    MONSTER_FLOOR_POWER_PER_LEVEL,
    MONSTER_FLOOR10_MAJOR_BOSS_MULT,
    MONSTER_FLOOR20_SLIME_KING_ARMOR_PENETRATION,
    MONSTER_FLOOR20_SLIME_KING_STAT_MULT,
    MONSTER_FLOOR20_SLIME_KING_TEMPLATE_KEY,
    MONSTER_FLOOR18_19_FLOORS,
    MONSTER_FLOOR18_19_MULT,
    MONSTER_HP_FLOOR12_MULT,
    MONSTER_HP_FLOOR12_THRESHOLD,
    MONSTER_FLOOR5_MINIBOSS_EXTRA_MULT,
    MONSTER_FLOOR5_MINIBOSS_HP_CAP,
    MONSTER_POST_FLOOR5_EXTRA_MULT_PER_FLOOR,
    MONSTER_HP_CURVE_MULT,
    MONSTER_HP_RAW_BASE,
    MONSTER_HP_RAW_PER_FLOOR,
    MONSTER_LATE_ATK_MULT,
    MONSTER_LATE_FLOOR_THRESHOLD,
    MONSTER_LATE_HP_MULT,
    MONSTER_MULT_ELITE_ATK,
    MONSTER_MULT_ELITE_HP,
    MONSTER_MULT_MAJOR_ATK,
    MONSTER_MULT_MAJOR_HP,
    MONSTER_MULT_MINI_ATK,
    MONSTER_MULT_MINI_HP,
    monster_tower_floor_strength_multiplier,
)
from game.enemies.floors.spawns import FloorMonsterSpawn


def monster_accuracy_evasion_for_spawn(floor_number: int, spawn: FloorMonsterSpawn) -> tuple[float, float]:
    """Точность / уклонение врага (доли 0..1) для этажа и роли спавна."""
    fl = int(floor_number)
    span = max(0, fl - 5)
    acc = span * float(MONSTER_ACCURACY_PER_FLOOR_AFTER_5)
    ev = span * float(MONSTER_EVASION_PER_FLOOR_AFTER_5)
    if spawn.is_elite:
        acc += float(MONSTER_ACCURACY_ELITE_ADD)
        ev += float(MONSTER_EVASION_ELITE_ADD)
    if spawn.is_mini_boss:
        acc += float(MONSTER_ACCURACY_MINI_ADD)
        ev += float(MONSTER_EVASION_MINI_ADD)
    if spawn.is_major_boss:
        acc += float(MONSTER_ACCURACY_MAJOR_ADD)
        ev += float(MONSTER_EVASION_MAJOR_ADD)
    acc = min(float(MONSTER_ACCURACY_CAP), max(0.0, acc))
    ev = min(float(MONSTER_EVASION_CAP), max(0.0, ev))
    return acc, ev


def monster_post_floor5_strength_mult(floor_number: int) -> float:
    fl = int(floor_number)
    if fl < 6:
        return 1.0
    return 1.0 + (fl - 5) * float(MONSTER_POST_FLOOR5_EXTRA_MULT_PER_FLOOR)


def apply_floor_difficulty_tiers(
    hp: int,
    atk: int,
    defense: int,
    floor_number: int,
) -> tuple[int, int, int]:
    """Прогрессивное усиление мобов по ярусу (общий путь формулы и каталога)."""
    fl = int(floor_number)
    if fl >= 71:
        hp_m, atk_m, def_m = 5.0, 3.8, 3.5
    elif fl >= 61:
        hp_m, atk_m, def_m = 4.0, 3.2, 3.0
    elif fl >= 50:
        hp_m, atk_m, def_m = 3.0, 2.6, 2.4
    elif fl >= 30:
        hp_m, atk_m, def_m = 1.70, 1.55, 1.55
    elif fl >= 20:
        hp_m, atk_m, def_m = 1.40, 1.30, 1.30
    else:
        return max(1, hp), max(1, atk), max(0, defense)
    return (
        max(1, int(hp * hp_m)),
        max(1, int(atk * atk_m)),
        max(0, int(defense * def_m)),
    )


def monster_strike_ailment(
    floor_number: int,
    spawn: FloorMonsterSpawn,
) -> tuple[float, str, str]:
    if spawn.is_elite or spawn.is_mini_boss or spawn.is_major_boss:
        take = True
    else:
        h = (int(floor_number) * 7919 + abs(hash(spawn.template.key))) % 100
        take = h < 40
    if not take:
        return 0.0, "", ""
    opts: tuple[tuple[float, str, str], ...] = (
        (0.055, "огнём", "🔥"),
        (0.05, "ядом", "☠️"),
        (0.045, "морозом", "❄️"),
        (0.045, "молнией", "⚡"),
        (0.04, "порчей", "🌑"),
    )
    i = abs(hash(spawn.template.key) + int(floor_number) * 17) % len(opts)
    mult, lab, em = opts[i]
    return mult, lab, em


def compute_formula_stat_bundle(floor_number: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    """Статы без каталога: классические кривые по этажу и типу цели."""
    raw_hp = MONSTER_HP_RAW_BASE + floor_number * MONSTER_HP_RAW_PER_FLOOR
    hp = int(raw_hp * MONSTER_HP_CURVE_MULT)
    raw_atk = MONSTER_ATK_RAW_BASE + floor_number // MONSTER_ATK_RAW_DIV_FLOOR
    atk = max(1, int(raw_atk * MONSTER_ATK_CURVE_MULT))
    defense = max(0, int((MONSTER_DEF_BASE + floor_number // MONSTER_DEF_DIV_FLOOR) * MONSTER_DEF_CURVE_MULT))
    mult_hp = 1.0
    mult_atk = 1.0
    if spawn.is_elite:
        mult_hp *= MONSTER_MULT_ELITE_HP
        mult_atk *= MONSTER_MULT_ELITE_ATK
    if spawn.is_mini_boss:
        mult_hp *= MONSTER_MULT_MINI_HP
        mult_atk *= MONSTER_MULT_MINI_ATK
    if spawn.is_major_boss:
        mult_hp *= MONSTER_MULT_MAJOR_HP
        mult_atk *= MONSTER_MULT_MAJOR_ATK
    if floor_number >= MONSTER_LATE_FLOOR_THRESHOLD:
        mult_hp *= MONSTER_LATE_HP_MULT
        mult_atk *= MONSTER_LATE_ATK_MULT
    atk_final = max(1, int(atk * mult_atk))
    atk_final += MONSTER_ATK_FLAT_ELITE if spawn.is_elite else MONSTER_ATK_FLAT_NORMAL

    lv = max(0, floor_number - 1)
    pwr = 1.0 + lv * MONSTER_FLOOR_POWER_PER_LEVEL
    dfn = 1.0 + lv * MONSTER_FLOOR_DEF_PER_LEVEL

    tower_m = monster_tower_floor_strength_multiplier(floor_number)
    if floor_number == 5 and spawn.is_mini_boss:
        tower_m *= MONSTER_FLOOR5_MINIBOSS_EXTRA_MULT

    hp_out = max(1, int(hp * mult_hp * pwr * tower_m))
    atk_out = max(1, int(atk_final * pwr * tower_m))
    def_out = max(0, int(defense * dfn * tower_m))

    post5 = monster_post_floor5_strength_mult(floor_number)
    hp_out = max(1, int(hp_out * post5))
    atk_out = max(1, int(atk_out * post5))
    def_out = max(0, int(def_out * post5))

    if int(floor_number) == 10 and spawn.is_major_boss:
        m10 = float(MONSTER_FLOOR10_MAJOR_BOSS_MULT)
        hp_out = max(1, int(hp_out * m10))
        atk_out = max(1, int(atk_out * m10))
        def_out = max(0, int(def_out * m10))

    if int(floor_number) >= MONSTER_HP_FLOOR12_THRESHOLD:
        hp_out = max(1, int(hp_out * MONSTER_HP_FLOOR12_MULT))

    if int(floor_number) in MONSTER_FLOOR18_19_FLOORS:
        m1819 = float(MONSTER_FLOOR18_19_MULT)
        hp_out = max(1, int(hp_out * m1819))
        atk_out = max(1, int(atk_out * m1819))
        def_out = max(0, int(def_out * m1819))

    # Прогрессивные ярусы 20+ — в apply_floor_difficulty_tiers (вызывается из combat_service).

    if (
        int(floor_number) == 20
        and spawn.is_major_boss
        and str(spawn.template.key) == MONSTER_FLOOR20_SLIME_KING_TEMPLATE_KEY
    ):
        msk = float(MONSTER_FLOOR20_SLIME_KING_STAT_MULT)
        hp_out = max(1, int(hp_out * msk))
        atk_out = max(1, int(atk_out * msk))
        def_out = max(0, int(def_out * msk))

    if int(floor_number) == 5 and spawn.is_mini_boss:
        hp_out = max(1, int(MONSTER_FLOOR5_MINIBOSS_HP_CAP))

    if (
        int(floor_number) >= 10
        and not spawn.is_elite
        and not spawn.is_mini_boss
        and not spawn.is_major_boss
    ):
        atk_out = max(1, int(atk_out) + 8)

    ail_mult, ail_lab, ail_em = monster_strike_ailment(floor_number, spawn)
    acc_v, ev_v = monster_accuracy_evasion_for_spawn(int(floor_number), spawn)
    bundle: dict[str, Any] = {
        "name": spawn.template.name,
        "emoji": spawn.template.emoji,
        "template_key": spawn.template.key,
        "hp": hp_out,
        "max_hp": hp_out,
        "atk": atk_out,
        "defense": def_out,
        "element": spawn.template.element or "earth",
        "accuracy": acc_v,
        "evasion": ev_v,
        "strike_ailment_mult": ail_mult,
        "strike_ailment_label_ru": ail_lab,
        "strike_ailment_emoji": ail_em,
    }
    if (
        int(floor_number) == 20
        and spawn.is_major_boss
        and str(spawn.template.key) == MONSTER_FLOOR20_SLIME_KING_TEMPLATE_KEY
    ):
        bundle["armor_penetration"] = float(MONSTER_FLOOR20_SLIME_KING_ARMOR_PENETRATION)
        bundle["applies_poison_on_hit"] = True
    return bundle
