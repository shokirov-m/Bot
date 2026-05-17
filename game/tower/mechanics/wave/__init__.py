"""Волны врагов (этажи 10, 27)."""

from . import wave_floor, wave_floor_27
from .instances import BY_FLOOR, MECH_27, mechanic_for_floor

__all__ = [
    "BY_FLOOR",
    "MECH_27",
    "mechanic_for_floor",
    "wave_floor",
    "wave_floor_27",
]
