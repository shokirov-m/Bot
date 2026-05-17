"""Исследование этажа (этажи 4, 8, 22)."""

from . import explore_floor, explore_floor_22, explore_floor_4
from .instances import BY_FLOOR, MECH_8, mechanic_for_floor

__all__ = [
    "BY_FLOOR",
    "MECH_8",
    "explore_floor",
    "explore_floor_4",
    "explore_floor_22",
    "mechanic_for_floor",
]
