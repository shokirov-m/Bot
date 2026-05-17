"""Этаж 30 — тёмный периметр."""

from game.tower.mechanics.room_clear.engine import expose_legacy_module
from game.tower.mechanics.room_clear.instances import MECH_30

_exports = expose_legacy_module(
    MECH_30,
    is_floor_name="is_room_clear_floor_30",
    all_slots_name="ROOM_CLEAR_30_ALL_SLOTS",
)
globals().update(_exports)

__all__ = list(_exports.keys())
