"""
Player Skills Management (Archetype 2.0 Integration).
"""
from __future__ import annotations
from typing import Any
from db.models.character import Character
from game.archetypes import manager as arch_manager
from game.characters.skills import SkillDef, skills_for_class

# Compatibility shim: skills are now tree-based, not shop-based.
# Populated lazily so it reflects all registered archetype skills.
def _build_skill_by_key() -> dict[str, SkillDef]:
    result: dict[str, SkillDef] = {}
    from game.archetypes.data import SKILLS
    for key, sk in SKILLS.items():
        result[key] = SkillDef(
            key=sk.key,
            name=sk.name_ru,
            mp_cost=int(sk.mp_cost),
            cooldown=int(sk.cooldown),
            power=float(sk.power_mult),
            kind=str(sk.kind),
            effect_key=sk.effect_key,
            effect_chance=float(sk.effect_chance),
        )
    return result


SKILL_BY_KEY: dict[str, SkillDef] = _build_skill_by_key()

# Skills are no longer purchased at the temple — now unlocked via skill tree.
# Kept as empty dict for API compatibility.
TEMPLE_SKILL_PRICES_GOLD: dict[str, int] = {}

def ensure_skill_meta(character: Character) -> None:
    """No longer strictly needed for unlocking, but keeps meta healthy."""
    pass

def learned_skill_keys(character: Character) -> set[str]:
    arch = arch_manager.get_character_archetype(character)
    return set(arch.skills)

def equipped_skill_key_slots(character: Character) -> list[str]:
    # Use meta_progress to get equipped skills or default to first 3 unlocked
    meta = character.meta_progress or {}
    eq = meta.get("equipped_skill_keys", [])
    if not eq:
        # Default to unlocked skills
        unlocked = [sk.key for sk in arch_manager.get_unlocked_skills(character)]
        eq = unlocked[:3]
        
    res = list(eq)
    while len(res) < 3:
        res.append("")
    return res

def battle_skills_tuple(character: Character) -> tuple[SkillDef, SkillDef, SkillDef]:
    # Pass character to skills_for_class to use Tree skills
    return skills_for_class(str(character.class_key or "wanderer"), character=character)

def set_equipped_slot(character: Character, slot_index: int, skill_key: str | None) -> bool:
    if slot_index < 0 or slot_index > 2:
        return False
    
    unlocked_keys = {sk.key for sk in arch_manager.get_unlocked_skills(character)}
    if skill_key and skill_key not in unlocked_keys:
        return False
        
    meta = dict(character.meta_progress or {})
    eq = list(meta.get("equipped_skill_keys", []))
    while len(eq) < 3:
        eq.append("")
        
    eq[slot_index] = skill_key or ""
    meta["equipped_skill_keys"] = eq
    character.meta_progress = meta
    return True

def try_buy_temple_skill(character: Character, skill_key: str) -> tuple[bool, str]:
    return False, "Навыки теперь открываются автоматически при выборе пути."

def skill_shop_summary_html(locale: str) -> str:
    return "<i>Выберите путь (Архетип) для получения новых навыков.</i>"

def shop_offer_skill_defs() -> list[Any]:
    return []

def describe_skill_for_ui(sk: SkillDef, locale: str) -> str:
    return f"MP {sk.mp_cost} · CD {sk.cooldown} · Сила ×{sk.power:.1f}"
