"""Экземпляры room-clear по этажам (данные в instances_data, логика в engine)."""

from __future__ import annotations

from game.tower.mechanics.room_clear.engine import RoomClearMechanic
from game.tower.mechanics.room_clear.instances_data import (
    CONFIG_10,
    CONFIG_24,
    CONFIG_26,
    CONFIG_30,
    CONFIG_40,
    CONFIG_5,
)

MECH_5 = RoomClearMechanic(CONFIG_5)
MECH_10 = RoomClearMechanic(CONFIG_10)
MECH_24 = RoomClearMechanic(CONFIG_24)
MECH_26 = RoomClearMechanic(CONFIG_26)
MECH_30 = RoomClearMechanic(CONFIG_30)
MECH_40 = RoomClearMechanic(CONFIG_40)

BY_FLOOR: dict[int, RoomClearMechanic] = {
    5: MECH_5,
    10: MECH_10,
    24: MECH_24,
    26: MECH_26,
    30: MECH_30,
    40: MECH_40,
}


def mechanic_for_floor(floor_number: int) -> RoomClearMechanic | None:
    return BY_FLOOR.get(int(floor_number))
