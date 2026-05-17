"""Применение выбора базового класса (17) и подкласса (57)."""

from __future__ import annotations

from db.models.character import Character
from game.characters.class_arcs import (
    SUBCLASS_BY_CLASS,
    SUBCLASS_NAME_RU,
    needs_base_class_choice,
    needs_subclass_choice,
)
from game.characters.classes import get_class_or_none
from services.progression.character_service import _compute_hp_max, _compute_mp_max

_WAND = get_class_or_none("wanderer")


def _base_class_stat_deltas(class_key: str) -> dict[str, int] | None:
    """Разница шаблона класса к страннику: +/− к текущим статам игрока."""
    if _WAND is None:
        return None
    cls = get_class_or_none(class_key)
    if cls is None:
        return None
    return {
        "strength": int(cls.strength) - int(_WAND.strength),
        "dexterity": int(cls.dexterity) - int(_WAND.dexterity),
        "intelligence": int(cls.intelligence) - int(_WAND.intelligence),
        "vitality": int(cls.vitality) - int(_WAND.vitality),
        "luck": int(cls.luck) - int(_WAND.luck),
    }


def apply_base_class(character: Character, class_key: str) -> bool:
    """Пассивный шаблон класса: дельты статов к текущим значениям; tier → 1."""
    if not needs_base_class_choice(character):
        return False
    cls = get_class_or_none(class_key)
    if cls is None:
        return False
    deltas = _base_class_stat_deltas(class_key)
    if deltas is None:
        return False
    hp_ratio = int(character.hp_current) / max(1, int(character.hp_max))
    mp_ratio = int(character.mp_current) / max(1, int(character.mp_max))

    character.stat_strength = max(3, int(character.stat_strength) + deltas["strength"])
    character.stat_dexterity = max(3, int(character.stat_dexterity) + deltas["dexterity"])
    character.stat_intelligence = max(3, int(character.stat_intelligence) + deltas["intelligence"])
    character.stat_vitality = max(3, int(character.stat_vitality) + deltas["vitality"])
    character.stat_luck = max(1, int(character.stat_luck) + deltas["luck"])

    character.class_key = cls.key
    character.class_tier = 1

    character.hp_max = max(1, _compute_hp_max(character.stat_vitality, character.stat_strength, cls))
    character.mp_max = max(0, _compute_mp_max(character.stat_intelligence, cls))
    character.hp_current = max(1, min(character.hp_max, int(character.hp_max * hp_ratio)))
    character.mp_current = max(0, min(character.mp_max, int(character.mp_max * mp_ratio)))

    if cls.default_element:
        character.element = cls.default_element
    return True


def apply_subclass(character: Character, subclass_key: str) -> bool:
    """Удвоение всех пяти статов, пересчёт HP/MP; tier → 2."""
    if not needs_subclass_choice(character):
        return False
    if subclass_key not in set(SUBCLASS_NAME_RU.keys()):
        return False
    allowed = set(SUBCLASS_BY_CLASS.get(character.class_key, ()))
    if subclass_key not in allowed:
        return False

    character.stat_strength = int(character.stat_strength) * 2
    character.stat_dexterity = int(character.stat_dexterity) * 2
    character.stat_intelligence = int(character.stat_intelligence) * 2
    character.stat_vitality = int(character.stat_vitality) * 2
    character.stat_luck = int(character.stat_luck) * 2

    cls = get_class_or_none(character.class_key)
    if cls is None:
        return False
    character.hp_max = max(1, _compute_hp_max(character.stat_vitality, character.stat_strength, cls))
    character.mp_max = max(0, _compute_mp_max(character.stat_intelligence, cls))
    character.hp_current = min(int(character.hp_current), character.hp_max)
    character.mp_current = min(int(character.mp_current), character.mp_max)
    character.subclass_key = subclass_key
    character.class_tier = 2
    return True


def subclass_display_ru(subclass_key: str | None) -> str | None:
    if not subclass_key:
        return None
    return SUBCLASS_NAME_RU.get(subclass_key)
