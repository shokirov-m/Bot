"""
Все скиллы классов и таблица боевых пассивов — редактируй здесь.
game/characters/skills.py собирает SkillDef из SKILL_DEFS_RAW.
"""

from __future__ import annotations

from typing import Any

PASSIVE_COMBAT_TABLE: dict[str, dict[str, float | int]] = {
    "wanderer": {"def_bonus": 2.0, "crit_bonus": 0.02, "dodge_bonus": 0.02, "mag_bonus_percent": 0, "mp_regen_turn": 2},
    "star_touched": {"def_bonus": 0.0, "crit_bonus": 0.08, "dodge_bonus": 0.06, "mag_bonus_percent": 12, "mp_regen_turn": 4},
    "tower_reaper": {"def_bonus": 4.0, "crit_bonus": 0.06, "dodge_bonus": 0.04, "mag_bonus_percent": 0, "mp_regen_turn": 0},
    "warrior": {"def_bonus": 10.0, "crit_bonus": 0.0, "dodge_bonus": 0.0, "mag_bonus_percent": 0, "mp_regen_turn": 0},
    "mage": {"def_bonus": 0.0, "crit_bonus": 0.0, "dodge_bonus": 0.0, "mag_bonus_percent": 20, "mp_regen_turn": 8},
    "archer": {"def_bonus": 0.0, "crit_bonus": 0.05, "dodge_bonus": 0.10, "mag_bonus_percent": 0, "mp_regen_turn": 0},
    "priest": {"def_bonus": 2.0, "crit_bonus": 0.0, "dodge_bonus": 0.0, "mag_bonus_percent": 0, "mp_regen_turn": 4},
    "assassin": {"def_bonus": 0.0, "crit_bonus": 0.20, "dodge_bonus": 0.15, "mag_bonus_percent": 0, "mp_regen_turn": 0},
    "berserker": {"def_bonus": 0.0, "crit_bonus": 0.08, "dodge_bonus": 0.0, "mag_bonus_percent": 0, "mp_regen_turn": 0},
    "necromancer": {"def_bonus": 0.0, "crit_bonus": 0.0, "dodge_bonus": 0.0, "mag_bonus_percent": 15, "mp_regen_turn": 0},
    "warden": {"def_bonus": 12.0, "crit_bonus": 0.0, "dodge_bonus": 0.0, "mag_bonus_percent": 0, "mp_regen_turn": 0},
    "shaman": {"def_bonus": 0.0, "crit_bonus": 0.0, "dodge_bonus": 0.0, "mag_bonus_percent": 10, "mp_regen_turn": 3},
    "hunter": {"def_bonus": 0.0, "crit_bonus": 0.06, "dodge_bonus": 0.08, "mag_bonus_percent": 0, "mp_regen_turn": 0},
}

SKILL_DEFS_RAW: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = {
    "wanderer": (
        {"key": "wn1", "name": "⚔️ Простой удар", "mp_cost": 12, "cooldown": 0, "power": 1.20, "kind": "phys"},
        {"key": "wn2", "name": "🛡️ Отход в защиту", "mp_cost": 18, "cooldown": 2, "power": 0.0, "kind": "phys", "effect_key": "block_next", "effect_chance": 0.75},
        {"key": "wn3", "name": "💨 Рывок", "mp_cost": 14, "cooldown": 3, "power": 1.10, "kind": "phys"},
    ),
    "star_touched": (
        {"key": "st1", "name": "✨ Звёздный укол", "mp_cost": 18, "cooldown": 0, "power": 1.65, "kind": "mag", "effect_key": "burn", "effect_chance": 0.15},
        {"key": "st2", "name": "🌠 Уклонение судьбы", "mp_cost": 22, "cooldown": 3, "power": 0.0, "kind": "mag", "effect_key": "dodge_buff", "effect_chance": 1.0},
        {"key": "st3", "name": "💫 Пульс эфира", "mp_cost": 28, "cooldown": 3, "power": 1.55, "kind": "mag", "effect_key": "paralyze", "effect_chance": 0.2},
    ),
    "tower_reaper": (
        {"key": "tr1", "name": "☠️ Режущий ветер", "mp_cost": 14, "cooldown": 0, "power": 1.75, "kind": "phys", "effect_key": "bleed", "effect_chance": 0.25},
        {"key": "tr2", "name": "🩸 Сбор долга", "mp_cost": 18, "cooldown": 2, "power": 1.35, "kind": "phys", "effect_key": "drain", "effect_chance": 0.15},
        {"key": "tr3", "name": "💀 Круг усталости", "mp_cost": 26, "cooldown": 3, "power": 1.60, "kind": "phys", "effect_key": "slow", "effect_chance": 0.3},
    ),
    "warrior": (
        {"key": "w1", "name": "🗡️ Мощный удар", "mp_cost": 15, "cooldown": 0, "power": 1.80, "kind": "phys"},
        {"key": "w2", "name": "🛡️ Щитовой блок", "mp_cost": 20, "cooldown": 2, "power": 0.0, "kind": "phys", "effect_key": "block_next", "effect_chance": 1.0},
        {"key": "w3", "name": "💢 Сокрушение", "mp_cost": 25, "cooldown": 3, "power": 1.10, "kind": "phys", "effect_key": "shred_armor", "effect_chance": 1.0},
    ),
    "mage": (
        {"key": "m1", "name": "🔥 Огненный шар", "mp_cost": 20, "cooldown": 0, "power": 2.00, "kind": "mag", "effect_key": "burn", "effect_chance": 0.40},
        {"key": "m2", "name": "❄️ Ледяные оковы", "mp_cost": 30, "cooldown": 3, "power": 1.50, "kind": "mag", "effect_key": "freeze", "effect_chance": 0.35},
        {"key": "m3", "name": "⚡ Цепная молния", "mp_cost": 35, "cooldown": 4, "power": 1.70, "kind": "mag", "effect_key": "paralyze", "effect_chance": 0.30},
    ),
    "archer": (
        {"key": "a1", "name": "🎯 Прицельный выстрел", "mp_cost": 12, "cooldown": 0, "power": 1.90, "kind": "phys"},
        {"key": "a2", "name": "💨 Отступление", "mp_cost": 18, "cooldown": 3, "power": 0.0, "kind": "phys", "effect_key": "dodge_buff", "effect_chance": 1.0},
        {"key": "a3", "name": "🌧️ Залп стрел", "mp_cost": 28, "cooldown": 3, "power": 1.60, "kind": "phys"},
    ),
    "priest": (
        {"key": "p1", "name": "💚 Исцеление", "mp_cost": 25, "cooldown": 0, "power": 0.0, "kind": "mag", "effect_key": "heal", "effect_chance": 1.0},
        {"key": "p2", "name": "🛡️ Святой щит", "mp_cost": 22, "cooldown": 3, "power": 0.0, "kind": "mag", "effect_key": "shield", "effect_chance": 1.0},
        {"key": "p3", "name": "☀️ Кара нечисти", "mp_cost": 30, "cooldown": 3, "power": 1.80, "kind": "mag"},
    ),
    "assassin": (
        {"key": "as1", "name": "🗡️ Удар в спину", "mp_cost": 15, "cooldown": 0, "power": 2.20, "kind": "phys", "effect_key": "backstab", "effect_chance": 1.0},
        {"key": "as2", "name": "💨 Дымовая завеса", "mp_cost": 25, "cooldown": 3, "power": 0.0, "kind": "phys", "effect_key": "smoke", "effect_chance": 1.0},
        {"key": "as3", "name": "☠️ Отравленный клинок", "mp_cost": 20, "cooldown": 2, "power": 1.30, "kind": "phys", "effect_key": "poison", "effect_chance": 0.5},
    ),
    "berserker": (
        {"key": "b1", "name": "🩸 Кровожадность", "mp_cost": 10, "cooldown": 0, "power": 1.50, "kind": "phys", "effect_key": "self_bleed", "effect_chance": 0.2},
        {"key": "b2", "name": "💥 Яростный вихрь", "mp_cost": 28, "cooldown": 3, "power": 1.70, "kind": "phys"},
        {"key": "b3", "name": "🔥 Жертва крови", "mp_cost": 22, "cooldown": 3, "power": 2.00, "kind": "phys", "effect_key": "low_hp_bonus", "effect_chance": 1.0},
    ),
    "necromancer": (
        {"key": "n1", "name": "☠️ Касание смерти", "mp_cost": 22, "cooldown": 0, "power": 1.90, "kind": "mag", "effect_key": "drain", "effect_chance": 0.25},
        {"key": "n2", "name": "🦴 Призыв скелета", "mp_cost": 26, "cooldown": 4, "power": 1.40, "kind": "mag"},
        {"key": "n3", "name": "🌑 Пожирание жизни", "mp_cost": 30, "cooldown": 4, "power": 1.80, "kind": "mag", "effect_key": "drain", "effect_chance": 0.4},
    ),
    "warden": (
        {"key": "wd1", "name": "🛡️ Удар щитом", "mp_cost": 18, "cooldown": 0, "power": 1.60, "kind": "phys", "effect_key": "stun", "effect_chance": 0.25},
        {"key": "wd2", "name": "⛓️ Оковы", "mp_cost": 24, "cooldown": 3, "power": 1.20, "kind": "phys", "effect_key": "slow", "effect_chance": 0.4},
        {"key": "wd3", "name": "🏔️ Несокрушимый", "mp_cost": 26, "cooldown": 4, "power": 0.0, "kind": "phys", "effect_key": "fortify", "effect_chance": 1.0},
    ),
    "shaman": (
        {"key": "sh1", "name": "⚡ Удар духов", "mp_cost": 20, "cooldown": 0, "power": 1.75, "kind": "mag"},
        {"key": "sh2", "name": "🌿 Тотем исцеления", "mp_cost": 24, "cooldown": 3, "power": 0.0, "kind": "mag", "effect_key": "hot", "effect_chance": 1.0},
        {"key": "sh3", "name": "🌩️ Шторм предков", "mp_cost": 32, "cooldown": 4, "power": 1.65, "kind": "mag", "effect_key": "paralyze", "effect_chance": 0.25},
    ),
    "hunter": (
        {"key": "h1", "name": "🏹 Укус волка", "mp_cost": 14, "cooldown": 0, "power": 1.85, "kind": "phys", "effect_key": "bleed", "effect_chance": 0.3},
        {"key": "h2", "name": "🪤 Капкан", "mp_cost": 20, "cooldown": 3, "power": 1.10, "kind": "phys", "effect_key": "root", "effect_chance": 0.35},
        {"key": "h3", "name": "🌲 Звериный натиск", "mp_cost": 26, "cooldown": 3, "power": 1.70, "kind": "phys"},
    ),
}

CLASSES: dict[str, dict[str, Any]] = {
    cls_key: {
        "key": cls_key,
        "skills": {str(row["key"]): dict(row) for row in triple},
    }
    for cls_key, triple in SKILL_DEFS_RAW.items()
}


def get_class(class_key: str) -> dict[str, Any] | None:
    """Минимальный профиль класса (скиллы); расширяйте при переносе лора и стартового лута."""
    return CLASSES.get(class_key)


def get_subclass(subclass_key: str) -> dict[str, Any] | None:
    return None
