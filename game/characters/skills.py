"""
Bridge between Archetype 2.0 and the existing Combat Engine.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from db.models.character import Character
from game.archetypes import manager as arch_manager
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

def _map_v2_to_def(v2) -> SkillDef:
    return SkillDef(
        v2.key, v2.name_ru, v2.mp_cost, v2.cooldown, v2.power_mult, v2.kind, 
        v2.effect_key, v2.effect_chance
    )

def skills_for_class(class_key: str, character: Character | None = None) -> tuple[SkillDef, SkillDef, SkillDef]:
    # If character is provided, use their unlocked skills from the tree
    if character:
        v2_list = arch_manager.get_unlocked_skills(character)
    else:
        # Fallback to base skills for the class
        arch = arch_manager.get_archetype(class_key) or arch_manager.get_archetype("wanderer")
        v2_list = [arch_manager.get_skill(sk_key) for sk_key in arch.skills]
        v2_list = [s for s in v2_list if s is not None]
    
    # Pad with empty strike if needed to reach exactly 3 slots for the engine
    while len(v2_list) < 3:
        v2_list.append(arch_manager.get_skill("wn_strike"))
        
    return (_map_v2_to_def(v2_list[0]), _map_v2_to_def(v2_list[1]), _map_v2_to_def(v2_list[2]))

def passive_combat_modifiers(class_key: str) -> dict[str, float]:
    arch = arch_manager.get_archetype(class_key) or arch_manager.get_archetype("wanderer")
    defaults = {
        "def_bonus": 0.0,
        "crit_bonus": 0.0,
        "dodge_bonus": 0.0,
        "mag_bonus_percent": 0,
        "mp_regen_turn": 0,
    }
    # Convert PassiveV2 to flat dict
    mods = {}
    for pas in arch.passives:
        for k, v in pas.modifiers.items():
            mods[k] = mods.get(k, 0) + v
            
    return {**defaults, **mods}

def passive_combat_modifiers_merged(character: Character) -> dict[str, float | int]:
    # Use new archetype passives
    base = passive_combat_modifiers(str(character.class_key or "wanderer"))
    
    # Бонусы из гримуаров (бывшее древо SP)
    grim_b = arch_manager.get_tree_bonuses(character)
    merged = merge_passive_row(base, grim_b)

    # Merge equipped passive slot bonus (если игрок выбрал конкретную пассивку)
    meta = character.meta_progress or {}
    eq_passive_key = meta.get("equipped_passive_key") or ""
    if eq_passive_key:
        from game.characters.player_skills import learned_passives

        for pas in learned_passives(character):
            if pas.key == eq_passive_key:
                merged = merge_passive_row(merged, dict(pas.modifiers))
                break

    merged = merge_passive_row(merged, path_passive_delta(character.meta_progress))
    merged = merge_passive_row(merged, global_passive_delta(character.meta_progress))
    merged = merge_passive_row(merged, pets_mod.pet_passive_delta(character))

    # Floor 0 passive (chosen at tutorial)
    from game.tower.mechanics.floor_zero import get_floor0_passive_modifiers
    merged = merge_passive_row(merged, get_floor0_passive_modifiers(character))
    return merged
