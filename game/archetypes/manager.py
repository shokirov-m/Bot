"""
Manager service for Archetypes 2.0.
"""
from __future__ import annotations
import html
from typing import Any
from sqlalchemy.orm.attributes import flag_modified

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

    if arch_key == "necromancer":
        from game.necromancer.service import can_purchase_necromancer

        return can_purchase_necromancer(character)

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

def get_character_tree(character: Character) -> dict[str, SkillTreeNode]:
    """Древо SP: у tier‑2 классов используется дерево родительского tier‑1 (ключи узлов те же)."""
    arch_key = str(character.class_key or "wanderer").lower()
    tree = TREES.get(arch_key)
    if tree:
        return tree
    parent_key = _TIER2_PARENT.get(arch_key)
    if parent_key:
        parent_tree = TREES.get(parent_key)
        if parent_tree:
            return parent_tree
    return {}

def get_unlocked_skills(character: Character) -> list[SkillV2]:
    """Активные навыки: база архетипа + изученные гримуары."""
    from game.archetypes.grimoires import get_unlocked_skill_keys_from_grimoires

    arch = get_character_archetype(character)
    res: list[SkillV2] = [SKILLS[sk_key] for sk_key in arch.skills if sk_key in SKILLS]
    for sk_key in get_unlocked_skill_keys_from_grimoires(character):
        sk = SKILLS.get(sk_key)
        if sk and all(existing.key != sk.key for existing in res):
            res.append(sk)
    return res

def get_tree_bonuses(character: Character) -> dict[str, float | int]:
    """Бонусы из изученных гримуаров (бывшие узлы древа SP)."""
    from game.archetypes.grimoires import get_grimoire_combat_bonuses

    return get_grimoire_combat_bonuses(character)


def format_skill_tree_node_effect_ru(node: SkillTreeNode) -> str:
    """Человекочитаемая расшифровка модификаторов узла (дополняет description_ru)."""
    val = node.value

    stat_labels = {
        "str": "СИЛ",
        "dex": "ЛОВ",
        "int": "ИНТ",
        "vit": "ВЫН",
        "luck": "УДА",
    }

    effect_hints_ru: dict[str, str] = {
        "heal": "моментальное восстановление HP",
        "block_next": "ослабление следующего удара по тебе",
        "shield": "щит, гасящий входящий урон",
        "dodge_buff": "временное усиление уклонения",
        "burn": "шанс поджога (урон во времени)",
        "freeze": "шанс заморозки / пропуска хода врагом",
        "poison": "шанс яда",
        "bleed": "шанс кровотечения",
        "stun": "шанс оглушения",
        "slow": "ослабление исходящего урона врага",
        "hot": "восстановление HP несколько ходов подряд",
        "fortify": "временный рост защиты",
        "shred_armor": "снижает броню цели",
        "backstab": "бонус урона при высоком HP врага",
        "low_hp_bonus": "бонус урона при низком HP игрока",
    }

    if node.node_type == "active_skill":
        sk = get_skill(str(val))
        if sk is None:
            return "• Активная способность (данные навыка не найдены)."
        kind_ru = "магический" if sk.kind == "mag" else "физический"
        lines_act: list[str] = [
            "• Режим: кнопка навыка в бою (один из первых трёх слотов)",
            f"• Ресурс: {sk.mp_cost} MP · перезарядка: {sk.cooldown} ход.",
            f"• Урон: {kind_ru} · множитель силы навыка ×{sk.power_mult:g}",
        ]
        hint = effect_hints_ru.get(str(sk.effect_key or ""))
        if hint:
            lines_act.append(f"• Механика: {hint}")
        elif sk.effect_key:
            lines_act.append(f"• Доп. эффект: {sk.effect_key}")
        return "\n".join(lines_act)

    if not isinstance(val, dict):
        return ""

    lines: list[str] = []

    if node.node_type == "stat_boost":
        for k in sorted(val.keys(), key=str):
            raw = val[k]
            label = stat_labels.get(str(k), str(k).upper())
            try:
                n = float(raw)
                if abs(n - round(n)) < 1e-9:
                    lines.append(f"• +{int(round(n))} к {label}")
                else:
                    lines.append(f"• +{n:g} к {label}")
            except (TypeError, ValueError):
                lines.append(f"• {label}: {raw}")
        return "\n".join(lines)

    if node.node_type != "passive_bonus":
        return ""

    passive_labels: dict[str, str] = {
        "def_bonus": "Защита",
        "atk_bonus_pct": "Физ. урон",
        "mag_bonus_percent": "Маг. урон",
        "lifesteal_percent": "Вампиризм (от урона)",
        "mp_regen_turn": "Реген MP за ход",
        "crit_bonus": "Шанс критического удара",
        "dodge_bonus": "Шанс уклонения",
        "on_hit_freeze_chance": "Шанс заморозки при попадании",
        "hp_regen_pct_turn": "Реген HP за ход (% от макс.)",
    }

    def fmt_pct_label(key: str, x: float) -> str:
        base = passive_labels.get(key, key)
        if key in {"crit_bonus", "dodge_bonus", "on_hit_freeze_chance", "hp_regen_pct_turn"} and x <= 1.0:
            return f"{base}: +{x * 100:.0f}%"
        if key in {"atk_bonus_pct", "mag_bonus_percent", "lifesteal_percent"}:
            return f"{base}: +{x:.0f}%"
        return f"{base}: +{x:g}"

    for key in sorted(val.keys(), key=str):
        raw = val[key]
        try:
            x = float(raw)
        except (TypeError, ValueError):
            lines.append(f"• {passive_labels.get(key, key)}: {raw}")
            continue
        if key == "mp_regen_turn":
            lines.append(f"• {passive_labels[key]}: +{int(round(x))}")
            continue
        if key == "def_bonus":
            lines.append(f"• {passive_labels[key]}: +{x:g}")
            continue
        lines.append(f"• {fmt_pct_label(key, x)}")

    return "\n".join(lines)


def format_skill_tree_passives_profile_html_ru(character: Character) -> str:
    """HTML-фрагмент: пассивные бонусы из изученных гримуаров."""
    from game.archetypes.grimoires import format_grimoires_profile_html_ru

    return format_grimoires_profile_html_ru(character)
