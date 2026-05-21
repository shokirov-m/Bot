"""
Player Skills Management (Archetype 2.0 Integration).
"""
from __future__ import annotations
from typing import Any
from db.models.character import Character
from game.archetypes import manager as arch_manager
from game.archetypes.models import PassiveV2
from game.characters.skills import SkillDef, skills_for_class


def skill_emoji(kind: str) -> str:
    """⚔️ для физ. навыков, 🔮 для магических."""
    return "🔮" if kind == "mag" else "⚔️"


def passive_emoji(modifiers: dict) -> str:
    """Эмодзи пассивки по типу модификатора."""
    if "mag_bonus_percent" in modifiers:
        return "🔮"
    if "crit_bonus" in modifiers:
        return "🎯"
    if "dodge_bonus" in modifiers:
        return "💨"
    if "mp_regen_turn" in modifiers:
        return "💧"
    return "🛡️"

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

def ensure_skill_meta(character: Character) -> None:
    """
    Нормализация meta_progress для боевых слотов и пассивки.
    """
    from game.archetypes.grimoires import migrate_tree_to_grimoires

    migrate_tree_to_grimoires(character)
    meta = dict(character.meta_progress or {})

    unlocked = [sk.key for sk in arch_manager.get_unlocked_skills(character)]
    unlocked_set = set(unlocked)

    # --- skills: 3 слота ---
    raw = meta.get("equipped_skill_keys")
    eq_in = raw if isinstance(raw, list) else []
    eq_norm: list[str] = []
    seen: set[str] = set()
    for x in eq_in:
        if len(eq_norm) >= 3:
            break
        k = str(x or "").strip()
        if not k:
            continue
        if k not in unlocked_set:
            continue
        if k in seen:
            continue
        seen.add(k)
        eq_norm.append(k)

    # заполнить свободные слоты первыми незадействованными открытыми
    for k in unlocked:
        if len(eq_norm) >= 3:
            break
        if k not in seen:
            seen.add(k)
            eq_norm.append(k)

    while len(eq_norm) < 3:
        eq_norm.append("")

    meta["equipped_skill_keys"] = eq_norm

    # --- passive slot ---
    from game.archetypes.grimoires import passive_grimoires_as_passives

    arch = arch_manager.get_character_archetype(character)
    available_passives = {p.key for p in getattr(arch, "passives", [])}
    available_passives |= {p.key for p in passive_grimoires_as_passives(character)}
    pk = str(meta.get("equipped_passive_key") or "").strip()
    if pk and pk not in available_passives:
        pk = ""
    meta["equipped_passive_key"] = pk

    character.meta_progress = meta
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(character, "meta_progress")
    except Exception:
        # В некоторых контекстах Character может быть не ORM-объектом; не критично.
        return

def learned_skill_keys(character: Character) -> set[str]:
    unlocked = arch_manager.get_unlocked_skills(character)
    return {sk.key for sk in unlocked}

def equipped_skill_key_slots(character: Character) -> list[str]:
    # Use meta_progress to get equipped skills or default to first 3 unlocked
    ensure_skill_meta(character)
    meta = character.meta_progress or {}
    eq = meta.get("equipped_skill_keys") or []
    res = list(eq) if isinstance(eq, list) else []
    while len(res) < 3:
        res.append("")
    return res[:3]

def battle_skills_tuple(character: Character) -> tuple[SkillDef, SkillDef, SkillDef]:
    """Возвращает 3 слота навыков для боя, уважая экипировку игрока."""
    all_unlocked = arch_manager.get_unlocked_skills(character)
    unlocked_by_key = {sk.key: sk for sk in all_unlocked}

    meta = character.meta_progress or {}
    equipped = list(meta.get("equipped_skill_keys") or [])

    result: list = []
    for key in equipped[:3]:
        if key and key in unlocked_by_key:
            result.append(unlocked_by_key[key])

    # Заполнить пустые слоты первыми незадействованными навыками
    used_keys = {sk.key for sk in result}
    for sk in all_unlocked:
        if len(result) >= 3:
            break
        if sk.key not in used_keys:
            result.append(sk)
            used_keys.add(sk.key)

    # Гарантируем ровно 3 слота
    fallback = arch_manager.get_skill("wn_strike")
    while len(result) < 3:
        result.append(fallback)

    from game.characters.skills import _map_v2_to_def
    return (_map_v2_to_def(result[0]), _map_v2_to_def(result[1]), _map_v2_to_def(result[2]))

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
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(character, "meta_progress")
    except Exception:
        pass
    return True

def learned_passives(character: Character) -> list[PassiveV2]:
    """Пассивки архетипа + из гримуаров."""
    from game.archetypes.grimoires import passive_grimoires_as_passives

    arch = arch_manager.get_character_archetype(character)
    return list(arch.passives) + passive_grimoires_as_passives(character)


def equipped_passive_key(character: Character) -> str | None:
    """Ключ экипированной пассивки из meta_progress."""
    meta = character.meta_progress or {}
    return meta.get("equipped_passive_key") or None


def set_passive_slot(character: Character, passive_key: str | None) -> bool:
    """Экипировать пассивку в отдельный слот. None — снять."""
    from game.archetypes.grimoires import passive_grimoires_as_passives

    arch = arch_manager.get_character_archetype(character)
    available_keys = {p.key for p in arch.passives}
    available_keys |= {p.key for p in passive_grimoires_as_passives(character)}
    if passive_key and passive_key not in available_keys:
        return False
    meta = dict(character.meta_progress or {})
    meta["equipped_passive_key"] = passive_key or ""
    character.meta_progress = meta
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(character, "meta_progress")
    except Exception:
        pass
    return True


def describe_skill_for_ui(sk: SkillDef, locale: str) -> str:
    return f"MP {sk.mp_cost} · CD {sk.cooldown} · Сила ×{sk.power:.1f}"
