"""
Manager service for Archetypes 2.0.
"""
from __future__ import annotations
from typing import Any
from db.models.character import Character
from game.archetypes.data import ARCHETYPES, SKILLS
from game.archetypes.models import Archetype, SkillV2, SkillTreeNode
from game.archetypes.trees import TREES

_STAT_ATTR = {
    "str": "stat_strength",
    "dex": "stat_dexterity",
    "int": "stat_intelligence",
    "vit": "stat_vitality",
    "luck": "stat_luck",
}

_TIER2_PARENT: dict[str, str] = {
    "guardian": "warrior",
    "berserker": "warrior",
    "pyromancer": "mage",
    "cryomancer": "mage",
    "assassin": "scout",
    "ranger": "scout",
    "paladin": "acolyte",
    "prophet": "acolyte",
}

def tier2_children(parent_key: str) -> list[str]:
    parent = str(parent_key or "").lower()
    return [child for child, p in _TIER2_PARENT.items() if p == parent]

def get_archetype(key: str) -> Archetype | None:
    return ARCHETYPES.get(key)

def get_skill(key: str) -> SkillV2 | None:
    return SKILLS.get(key)

def get_character_archetype(character: Character) -> Archetype:
    """Returns the current archetype of the character or Wanderer by default."""
    key = str(character.class_key or "wanderer").lower()
    return ARCHETYPES.get(key, ARCHETYPES["wanderer"])

def get_character_passives(character: Character) -> dict[str, float | int]:
    """Returns merged combat modifiers from the archetype."""
    arch = get_character_archetype(character)
    merged: dict[str, float | int] = {}
    for pas in arch.passives:
        for k, v in pas.modifiers.items():
            if k in merged:
                if isinstance(v, (int, float)):
                    merged[k] += v
            else:
                merged[k] = v
    return merged

def get_character_skills(character: Character) -> list[SkillV2]:
    """Returns list of SkillV2 objects the character currently has access to."""
    arch = get_character_archetype(character)
    return [SKILLS[sk_key] for sk_key in arch.skills if sk_key in SKILLS]

def get_character_stat_bonuses(character: Character) -> dict[str, int]:
    """Returns flat stat bonuses from the current archetype."""
    arch = get_character_archetype(character)
    # Ensure all STAT_KEYS are present
    out = {"str": 0, "dex": 0, "int": 0, "vit": 0, "luck": 0}
    for k, v in arch.base_stats.items():
        if k in out:
            out[k] = v
    return out

def can_unlock_archetype(character: Character, arch_key: str) -> tuple[bool, str]:
    """Checks if a character meets the requirements for a new archetype."""
    arch = ARCHETYPES.get(arch_key)
    if not arch:
        return False, "Неизвестный архетип."

    current_key = str(character.class_key or "wanderer").lower()
    current = ARCHETYPES.get(current_key, ARCHETYPES["wanderer"])
    if arch.tier <= current.tier and arch.key != current.key:
        return False, "Этот путь уже пройден или ниже текущего."
    if arch.tier == 1 and current.key != "wanderer":
        return False, "Базовый путь уже выбран."
    if arch.tier == 2 and _TIER2_PARENT.get(arch.key) != current.key:
        parent = ARCHETYPES.get(_TIER2_PARENT.get(arch.key, ""))
        parent_name = parent.name_ru if parent else "нужный базовый путь"
        return False, f"Сначала нужен путь: {parent_name}."
    
    if character.level < arch.requirements.get("level", 1):
        return False, f"Требуется уровень {arch.requirements['level']}."
        
    for stat, val in arch.requirements.items():
        if stat == "level": continue
        attr = _STAT_ATTR.get(stat, stat if stat.startswith("stat_") else f"stat_{stat}")
        if int(getattr(character, attr, 0)) < val:
            return False, f"Требуется {stat.upper()} {val}+."
            
    return True, "Условия выполнены."

# --- Skill Tree Logic ---

def get_character_sp(character: Character) -> int:
    """Returns unspent Skill Points from meta_progress."""
    return int((character.meta_progress or {}).get("unspent_sp", 0))

def get_unlocked_node_keys(character: Character) -> set[str]:
    """Returns set of unlocked tree node keys."""
    return set((character.meta_progress or {}).get("unlocked_nodes", []))

def get_character_tree(character: Character) -> dict[str, SkillTreeNode]:
    """Returns the skill tree for the character's current archetype."""
    arch_key = str(character.class_key or "wanderer").lower()
    return TREES.get(arch_key, {})

def get_unlocked_skills(character: Character) -> list[SkillV2]:
    """Returns list of active skills unlocked in the tree."""
    arch = get_character_archetype(character)
    res: list[SkillV2] = [SKILLS[sk_key] for sk_key in arch.skills if sk_key in SKILLS]
    tree = get_character_tree(character)
    unlocked = get_unlocked_node_keys(character)

    for node_key in unlocked:
        node = tree.get(node_key)
        if node and node.node_type == "active_skill":
            sk = SKILLS.get(str(node.value))
            if sk and all(existing.key != sk.key for existing in res):
                res.append(sk)
    return res

def get_tree_bonuses(character: Character) -> dict[str, float | int]:
    """Calculates total bonuses from unlocked nodes in the tree."""
    tree = get_character_tree(character)
    unlocked = get_unlocked_node_keys(character)
    merged: dict[str, float | int] = {}
    
    for node_key in unlocked:
        node = tree.get(node_key)
        if not node: continue
        
        if node.node_type in ("passive_bonus", "stat_boost") and isinstance(node.value, dict):
            for k, v in node.value.items():
                merged[k] = merged.get(k, 0) + v
                
    return merged

def try_unlock_node(character: Character, node_key: str) -> tuple[bool, str]:
    """Attempts to spend 1 SP and unlock a node."""
    tree = get_character_tree(character)
    node = tree.get(node_key)
    if not node:
        return False, "Узел не найден."
        
    unlocked = get_unlocked_node_keys(character)
    if node_key in unlocked:
        return False, "Узел уже изучен."
        
    sp = get_character_sp(character)
    if sp < node.cost_sp:
        return False, f"Недостаточно очков навыков (нужно {node.cost_sp})."
        
    # Check parents
    for p_key in node.parent_keys:
        if p_key not in unlocked:
            return False, f"Сначала нужно изучить: {tree[p_key].name_ru}."
            
    # Success
    mp = dict(character.meta_progress or {})
    mp["unspent_sp"] = sp - node.cost_sp
    node_list = list(unlocked)
    node_list.append(node_key)
    mp["unlocked_nodes"] = node_list
    character.meta_progress = mp
    
    return True, f"Изучено: {node.name_ru}!"
