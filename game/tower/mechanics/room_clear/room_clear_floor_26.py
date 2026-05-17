"""Этаж 26 — зал сомнений."""

from game.tower.mechanics.room_clear.engine import expose_legacy_module
from game.tower.mechanics.room_clear.instances import MECH_26

_exports = expose_legacy_module(
    MECH_26,
    is_floor_name="is_room_clear_floor_26",
    all_slots_name="ROOM_CLEAR_26_ALL_SLOTS",
)
globals().update(_exports)

__all__ = list(_exports.keys())
