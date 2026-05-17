"""Этаж 4 — исследование леса."""

from game.tower.mechanics.explore.engine import expose_legacy_module
from game.tower.mechanics.explore.instances import MECH_4

_exports = expose_legacy_module(
    MECH_4,
    is_floor_name="is_explore_floor_4",
    floor_const_name="EXPLORE_FLOOR_4",
    all_slots_name="EXPLORE_4_ALL_SLOTS",
)
globals().update(_exports)

__all__ = list(_exports.keys())
