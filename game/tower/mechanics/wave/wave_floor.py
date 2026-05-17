"""Этаж 10 — волны вторжения (legacy; на 10-м приоритет у room_clear)."""

from game.tower.mechanics.wave.engine import expose_legacy_module
from game.tower.mechanics.wave.instances import MECH_10

_exports = expose_legacy_module(
    MECH_10,
    is_floor_name="is_wave_floor",
    floor_const_name="WAVE_FLOOR",
    all_slots_name="WAVE_FLOOR_ALL_SLOTS",
    all_spawns_name="all_wave_floor_spawns",
    format_banner_name="format_wave_floor_banner_html",
)
globals().update(_exports)

__all__ = list(_exports.keys())
