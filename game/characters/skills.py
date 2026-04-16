"""
Активные скиллы классов (3 на класс) — стоимость MP, кулдаун, множитель силы.
effect_key — задел под статусы (поджог, заморозка, …).
"""

from __future__ import annotations

from dataclasses import dataclass

from db.models.character import Character
from game.characters.global_passives import global_passive_delta
from game.characters import pets as pets_mod
from game.characters.path_ranks import merge_passive_row, path_passive_delta


@dataclass(frozen=True, slots=True)
class SkillDef:
    key: str
    name: str
    mp_cost: int
    cooldown: int
    power: float
    kind: str  # phys | mag
    effect_key: str | None = None
    effect_chance: float = 0.0


CLASS_SKILLS: dict[str, tuple[SkillDef, SkillDef, SkillDef]] = {
    "wanderer": (
        SkillDef("wn1", "⚔️ Простой удар", 12, 0, 1.20, "phys"),
        SkillDef("wn2", "🛡️ Отход в защиту", 18, 2, 0.0, "phys", "block_next", 0.75),
        SkillDef("wn3", "💨 Рывок", 14, 3, 1.10, "phys"),
    ),
    "star_touched": (
        SkillDef("st1", "✨ Звёздный укол", 18, 0, 1.65, "mag", "burn", 0.15),
        SkillDef("st2", "🌠 Уклонение судьбы", 22, 3, 0.0, "mag", "dodge_buff", 1.0),
        SkillDef("st3", "💫 Пульс эфира", 28, 3, 1.55, "mag", "paralyze", 0.2),
    ),
    "tower_reaper": (
        SkillDef("tr1", "☠️ Режущий ветер", 14, 0, 1.75, "phys", "bleed", 0.25),
        SkillDef("tr2", "🩸 Сбор долга", 18, 2, 1.35, "phys", "drain", 0.15),
        SkillDef("tr3", "💀 Круг усталости", 26, 3, 1.60, "phys", "slow", 0.3),
    ),
    "warrior": (
        SkillDef("w1", "🗡️ Мощный удар", 15, 0, 1.80, "phys"),
        SkillDef("w2", "🛡️ Щитовой блок", 20, 2, 0.0, "phys", "block_next", 1.0),
        SkillDef("w3", "💢 Сокрушение", 25, 3, 1.10, "phys", "shred_armor", 1.0),
    ),
    "mage": (
        SkillDef("m1", "🔥 Огненный шар", 20, 0, 2.00, "mag", "burn", 0.40),
        SkillDef("m2", "❄️ Ледяные оковы", 30, 3, 1.50, "mag", "freeze", 0.35),
        SkillDef("m3", "⚡ Цепная молния", 35, 4, 1.70, "mag", "paralyze", 0.30),
    ),
    "archer": (
        SkillDef("a1", "🎯 Прицельный выстрел", 12, 0, 1.90, "phys"),
        SkillDef("a2", "💨 Отступление", 18, 3, 0.0, "phys", "dodge_buff", 1.0),
        SkillDef("a3", "🌧️ Залп стрел", 28, 3, 1.60, "phys"),
    ),
    "priest": (
        SkillDef("p1", "💚 Исцеление", 25, 0, 0.0, "mag", "heal", 1.0),
        SkillDef("p2", "🛡️ Святой щит", 22, 3, 0.0, "mag", "shield", 1.0),
        SkillDef("p3", "☀️ Кара нечисти", 30, 3, 1.80, "mag"),
    ),
    "assassin": (
        SkillDef("as1", "🗡️ Удар в спину", 15, 0, 2.20, "phys", "backstab", 1.0),
        SkillDef("as2", "💨 Дымовая завеса", 25, 3, 0.0, "phys", "smoke", 1.0),
        SkillDef("as3", "☠️ Отравленный клинок", 20, 2, 1.30, "phys", "poison", 0.5),
    ),
    "berserker": (
        SkillDef("b1", "🩸 Кровожадность", 10, 0, 1.50, "phys", "self_bleed", 0.2),
        SkillDef("b2", "💥 Яростный вихрь", 28, 3, 1.70, "phys"),
        SkillDef("b3", "🔥 Жертва крови", 22, 3, 2.00, "phys", "low_hp_bonus", 1.0),
    ),
    "necromancer": (
        SkillDef("n1", "☠️ Касание смерти", 22, 0, 1.90, "mag", "drain", 0.25),
        SkillDef("n2", "🦴 Призыв скелета", 26, 4, 1.40, "mag"),
        SkillDef("n3", "🌑 Пожирание жизни", 30, 4, 1.80, "mag", "drain", 0.4),
    ),
    "warden": (
        SkillDef("wd1", "🛡️ Удар щитом", 18, 0, 1.60, "phys", "stun", 0.25),
        SkillDef("wd2", "⛓️ Оковы", 24, 3, 1.20, "phys", "slow", 0.4),
        SkillDef("wd3", "🏔️ Несокрушимый", 26, 4, 0.0, "phys", "fortify", 1.0),
    ),
    "shaman": (
        SkillDef("sh1", "⚡ Удар духов", 20, 0, 1.75, "mag"),
        SkillDef("sh2", "🌿 Тотем исцеления", 24, 3, 0.0, "mag", "hot", 1.0),
        SkillDef("sh3", "🌩️ Шторм предков", 32, 4, 1.65, "mag", "paralyze", 0.25),
    ),
    "hunter": (
        SkillDef("h1", "🏹 Укус волка", 14, 0, 1.85, "phys", "bleed", 0.3),
        SkillDef("h2", "🪤 Капкан", 20, 3, 1.10, "phys", "root", 0.35),
        SkillDef("h3", "🌲 Звериный натиск", 26, 3, 1.70, "phys"),
    ),
}


def skills_for_class(class_key: str) -> tuple[SkillDef, SkillDef, SkillDef]:
    return CLASS_SKILLS.get(
        class_key,
        CLASS_SKILLS["wanderer"],
    )


def passive_combat_modifiers(class_key: str) -> dict[str, float]:
    """
    Упрощённые пассивы для формул боя.
    Ключи: def_bonus, crit_bonus, dodge_bonus, mag_bonus_percent, mp_regen_turn.
    """
    defaults = {
        "def_bonus": 0.0,
        "crit_bonus": 0.0,
        "dodge_bonus": 0.0,
        "mag_bonus_percent": 0,
        "mp_regen_turn": 0,
    }
    table: dict[str, dict[str, float | int]] = {
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
    row = table.get(class_key, table["wanderer"])
    return {**defaults, **row}  # type: ignore[arg-type]


def passive_combat_modifiers_merged(character: Character) -> dict[str, float | int]:
    """Класс + пассив звания (path_passive_key) + глобальные пассивы + активный питомец."""
    base = passive_combat_modifiers(character.class_key)
    merged = merge_passive_row(base, path_passive_delta(character.meta_progress))
    merged = merge_passive_row(merged, global_passive_delta(character.meta_progress))
    return merge_passive_row(merged, pets_mod.pet_passive_delta(character))
