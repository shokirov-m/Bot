"""Этаж 5 — зачистка комнат."""

from game.tower.mechanics.room_clear.engine import expose_legacy_module
from game.tower.mechanics.room_clear.instances import MECH_5

_exports = expose_legacy_module(
    MECH_5,
    is_floor_name="is_room_clear_floor",
    all_slots_name="ROOM_CLEAR_ALL_SLOTS",
)
globals().update(_exports)

__all__ = list(_exports.keys())
