"""Экземпляры wave по этажам."""

from __future__ import annotations

from game.tower.mechanics.wave.engine import WaveMechanic
from game.tower.mechanics.wave.instances_data import CONFIG_10, CONFIG_27

MECH_10 = WaveMechanic(CONFIG_10)
MECH_27 = WaveMechanic(CONFIG_27)

BY_FLOOR: dict[int, WaveMechanic] = {
    10: MECH_10,
    27: MECH_27,
}


def mechanic_for_floor(floor_number: int) -> WaveMechanic | None:
    return BY_FLOOR.get(int(floor_number))
