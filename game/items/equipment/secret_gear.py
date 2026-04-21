"""Тайник: предметы из каталога game/data/items/."""

from __future__ import annotations

import random
from typing import Any

from game.items.equipment.constants import (
    SECRET_GEAR_DROP_CHANCE,
    SECRET_GEAR_MAX_FLOOR,
)
from game.items import catalog_loot


def try_roll_secret_gear_payload(floor_number: int) -> dict[str, Any] | None:
    """Случайный предмет из каталога при обыске тайника на этаже."""
    if floor_number < 1 or floor_number > SECRET_GEAR_MAX_FLOOR:
        return None
    if random.random() >= SECRET_GEAR_DROP_CHANCE:
        return None
    return catalog_loot.roll_catalog_item(floor_number)
