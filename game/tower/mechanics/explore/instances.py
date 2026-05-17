"""Экземпляры explore по этажам."""

from __future__ import annotations

from game.tower.mechanics.explore.engine import ExploreMechanic
from game.tower.mechanics.explore.instances_data import CONFIG_22, CONFIG_4, CONFIG_8

MECH_4 = ExploreMechanic(CONFIG_4)
MECH_8 = ExploreMechanic(CONFIG_8)
MECH_22 = ExploreMechanic(CONFIG_22)

BY_FLOOR: dict[int, ExploreMechanic] = {
    4: MECH_4,
    8: MECH_8,
    22: MECH_22,
}


def mechanic_for_floor(floor_number: int) -> ExploreMechanic | None:
    return BY_FLOOR.get(int(floor_number))
