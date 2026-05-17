"""Этаж 10 — тёмные катакомбы."""

from game.tower.mechanics.room_clear.engine import expose_legacy_module
from game.tower.mechanics.room_clear.instances import MECH_10

_exports = expose_legacy_module(
    MECH_10,
    is_floor_name="is_room_clear_floor_10",
    all_slots_name="ROOM_CLEAR_10_ALL_SLOTS",
)
globals().update(_exports)

__all__ = list(_exports.keys())
