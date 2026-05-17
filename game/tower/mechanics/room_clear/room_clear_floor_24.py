"""Этаж 24 — пещеры теней."""

from game.tower.mechanics.room_clear.engine import expose_legacy_module
from game.tower.mechanics.room_clear.instances import MECH_24

_exports = expose_legacy_module(
    MECH_24,
    is_floor_name="is_room_clear_floor_24",
    all_slots_name="ROOM_CLEAR_24_ALL_SLOTS",
)
globals().update(_exports)

__all__ = list(_exports.keys())
