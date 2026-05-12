"""
Class Definitions (Archetype 2.0 Transition).
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ClassDefinition:
    key: str
    name_ru: str
    emoji: str
    strength: int
    dexterity: int
    intelligence: int
    vitality: int
    luck: int
    passive_ru: str
    skill_1: str
    skill_2: str
    skill_3: str
    default_element: str | None
    hp_multiplier: float = 1.0
    mp_multiplier: float = 1.0

CLASSES: dict[str, ClassDefinition] = {
    "wanderer": ClassDefinition(
        key="wanderer",
        name_ru="Странник",
        emoji="🎒",
        strength=10,
        dexterity=10,
        intelligence=10,
        vitality=10,
        luck=10,
        passive_ru="Ожидание пути...",
        skill_1="⚔️ Удар",
        skill_2="🛡️ Защита",
        skill_3="💨 Рывок",
        default_element=None,
    ),
}

def get_class_or_none(key: str) -> ClassDefinition | None:
    """Карточка класса для UI/боя по ключу архетипа (v2)."""
    from game.archetypes import manager as arch_manager
    from game.archetypes.data import SKILLS

    k = (key or "wanderer").strip().lower()
    arch = arch_manager.get_archetype(k)
    if arch is None:
        return None
    bs = arch.base_stats or {}
    sks = list(arch.skills)[:3]

    def _sk_name(i: int) -> str:
        if i >= len(sks):
            return "—"
        sk = SKILLS.get(str(sks[i]))
        return sk.name_ru if sk else str(sks[i])

    desc = (getattr(arch, "description_ru", None) or "").strip() or "—"
    passives = getattr(arch, "passives", ()) or ()
    passive_ru = desc
    if passives:
        passive_ru = (passives[0].description_ru or desc).strip() or desc

    return ClassDefinition(
        key=arch.key,
        name_ru=arch.name_ru,
        emoji=arch.emoji,
        strength=int(bs.get("str", 10)),
        dexterity=int(bs.get("dex", 10)),
        intelligence=int(bs.get("int", 10)),
        vitality=int(bs.get("vit", 10)),
        luck=int(bs.get("luck", 10)),
        passive_ru=passive_ru[:500],
        skill_1=_sk_name(0),
        skill_2=_sk_name(1),
        skill_3=_sk_name(2),
        default_element=None,
        hp_multiplier=float(arch.hp_multiplier),
        mp_multiplier=float(arch.mp_multiplier),
    )


def all_classes_ordered() -> list[ClassDefinition]:
    from game.archetypes.data import ARCHETYPES

    out: list[ClassDefinition] = []
    for arch in ARCHETYPES.values():
        cd = get_class_or_none(arch.key)
        if cd:
            out.append(cd)
    if not out:
        w = get_class_or_none("wanderer")
        return [w] if w else []
    return out
