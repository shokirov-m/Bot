"""Этаж 22 — исследование пещер теней."""

from game.tower.mechanics.explore.engine import expose_legacy_module
from game.tower.mechanics.explore.instances import MECH_22

_exports = expose_legacy_module(
    MECH_22,
    is_floor_name="is_explore_floor_22",
    floor_const_name="EXPLORE_FLOOR_22",
    all_slots_name="EXPLORE_22_ALL_SLOTS",
)
globals().update(_exports)

__all__ = list(_exports.keys())
