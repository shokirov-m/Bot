"""Примеры каталога экипировки — источник для инвентаря и тулов."""

from __future__ import annotations

from typing import Any

from game.data.items.amulets import amulet_examples
from game.data.items.armor import armor_examples, gloves_examples, helmet_examples, pants_examples
from game.data.items.offhand import grimoire_examples, shield_examples
from game.data.items.rings import ring_examples
from game.data.items.weapons import (
    two_handed_weapon_examples,
    weapon_main_examples,
    weapon_offhand_examples,
)


def all_example_groups() -> dict[str, list[dict[str, Any]]]:
    return {
        "weapon_main": weapon_main_examples(),
        "weapon_off": weapon_offhand_examples(),
        "two_handed": two_handed_weapon_examples(),
        "pants": pants_examples(),
        "armor": armor_examples(),
        "helmet": helmet_examples(),
        "gloves": gloves_examples(),
        "ring": ring_examples(),
        "amulet": amulet_examples(),
        "shield": shield_examples(),
        "grimoire": grimoire_examples(),
    }


__all__ = [
    "all_example_groups",
    "amulet_examples",
    "armor_examples",
    "gloves_examples",
    "grimoire_examples",
    "helmet_examples",
    "pants_examples",
    "ring_examples",
    "shield_examples",
    "two_handed_weapon_examples",
    "weapon_main_examples",
    "weapon_offhand_examples",
]
