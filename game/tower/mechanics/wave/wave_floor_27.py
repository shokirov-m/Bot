"""Этаж 27 — волны теней."""

from game.tower.mechanics.wave.engine import expose_legacy_module
from game.tower.mechanics.wave.instances import MECH_27

_exports = expose_legacy_module(
    MECH_27,
    is_floor_name="is_wave_floor_27",
    floor_const_name="WAVE_FLOOR_27",
    all_slots_name="WAVE_FLOOR_27_ALL_SLOTS",
    all_spawns_name="all_wave_floor_27_spawns",
    format_banner_name="format_wave_floor_27_banner_html",
)
globals().update(_exports)

__all__ = list(_exports.keys())
