"""Этаж 8 — исследование пещеры."""

from game.tower.mechanics.explore.engine import expose_legacy_module
from game.tower.mechanics.explore.instances import MECH_8

_exports = expose_legacy_module(
    MECH_8,
    is_floor_name="is_explore_floor",
    floor_const_name="EXPLORE_FLOOR",
    all_slots_name="EXPLORE_ALL_SLOTS",
)
globals().update(_exports)

__all__ = list(_exports.keys())
