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
    return CLASSES.get("wanderer")

def all_classes_ordered() -> list[ClassDefinition]:
    return [CLASSES["wanderer"]]
