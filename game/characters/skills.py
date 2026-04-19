"""
Активные скиллы классов (3 на класс) — стоимость MP, кулдаун, множитель силы.
effect_key — задел под статусы (поджог, заморозка, …).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from db.models.character import Character
from game.characters.global_passives import global_passive_delta
from game.characters import pets as pets_mod
from game.characters.path_ranks import merge_passive_row, path_passive_delta
from game.data.classes import PASSIVE_COMBAT_TABLE, SKILL_DEFS_RAW


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


def _skill_def_from_row(row: dict[str, Any]) -> SkillDef:
    return SkillDef(
        str(row["key"]),
        str(row["name"]),
        int(row["mp_cost"]),
        int(row["cooldown"]),
        float(row["power"]),
        str(row["kind"]),
        row.get("effect_key"),
        float(row.get("effect_chance", 0.0)),
    )


CLASS_SKILLS: dict[str, tuple[SkillDef, SkillDef, SkillDef]] = {
    cls: tuple(_skill_def_from_row(r) for r in triple) for cls, triple in SKILL_DEFS_RAW.items()
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
    row = PASSIVE_COMBAT_TABLE.get(class_key, PASSIVE_COMBAT_TABLE["wanderer"])
    return {**defaults, **row}  # type: ignore[arg-type]


def scale_passive_row(row: dict[str, float | int], factor: float) -> dict[str, float | int]:
    """Масштаб пассивов второй профессии (0.5)."""
    f = max(0.0, float(factor))
    out: dict[str, float | int] = {}
    for k, v in row.items():
        if k == "mp_regen_turn":
            out[k] = int(round(int(v) * f))
        elif k == "mag_bonus_percent":
            out[k] = int(round(int(v) * f))
        else:
            out[k] = float(v) * f
    return out


def passive_combat_modifiers_merged(character: Character) -> dict[str, float | int]:
    """Активная профессия (бой) + 50% пассивов второй (с 51 этажа) + звание + глобальные + питомец."""
    from services import profession_service

    primary = profession_service.primary_skill_class_for_passives(character)
    base = passive_combat_modifiers(primary)
    sec_key = profession_service.secondary_skill_class_for_passives(character)
    if sec_key:
        base = merge_passive_row(base, scale_passive_row(passive_combat_modifiers(sec_key), 0.5))
    merged = merge_passive_row(base, path_passive_delta(character.meta_progress))
    merged = merge_passive_row(merged, global_passive_delta(character.meta_progress))
    return merge_passive_row(merged, pets_mod.pet_passive_delta(character))
