"""Доступ к кузнице в городах-хабах (3, 31, 61, 91)."""

from __future__ import annotations

from game.floors import floor_data


def forge_available_on_floor(floor_number: int) -> bool:
    return floor_data.get_city_for_floor(floor_number) is not None
