"""Публичный API события «Золотой гоблин»."""

from game.enemies.events.golden_goblin_spawn import (
    FLOOR_MAX,
    FLOOR_MIN,
    SLOT_CODE,
    TEMPLATE_KEY,
    build_spawn,
    floor_accepts_golden_goblin_event,
)

__all__ = [
    "FLOOR_MAX",
    "FLOOR_MIN",
    "SLOT_CODE",
    "TEMPLATE_KEY",
    "build_spawn",
    "floor_accepts_golden_goblin_event",
]
