"""Этаж 40 — ледяной цитадельный пояс."""

from game.tower.mechanics.room_clear.engine import expose_legacy_module
from game.tower.mechanics.room_clear.instances import MECH_40

_exports = expose_legacy_module(
    MECH_40,
    is_floor_name="is_room_clear_floor_40",
    all_slots_name="ROOM_CLEAR_40_ALL_SLOTS",
)
globals().update(_exports)

__all__ = list(_exports.keys())
