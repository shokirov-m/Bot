"""Зачистка комнат на этажах 5, 10, 24, 26, 30, 40."""

from . import (
    room_clear_floor,
    room_clear_floor_10,
    room_clear_floor_24,
    room_clear_floor_26,
    room_clear_floor_30,
    room_clear_floor_40,
)
from .instances import BY_FLOOR, MECH_5, mechanic_for_floor

__all__ = [
    "BY_FLOOR",
    "MECH_5",
    "mechanic_for_floor",
    "room_clear_floor",
    "room_clear_floor_10",
    "room_clear_floor_24",
    "room_clear_floor_26",
    "room_clear_floor_30",
    "room_clear_floor_40",
]
