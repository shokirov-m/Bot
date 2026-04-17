"""Сводный реестр примеров предметов (файлы по типам в `catalog/`)."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog.amulets import amulet_examples
from game.items.equipment.catalog.chest_armor import armor_examples
from game.items.equipment.catalog.gloves import gloves_examples
from game.items.equipment.catalog.helmet import helmet_examples
from game.items.equipment.catalog.pants import pants_examples
from game.items.equipment.catalog.rings import ring_examples
from game.items.equipment.catalog.offhand import grimoire_examples, shield_examples
from game.items.equipment.catalog.weapons import (
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
