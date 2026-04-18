"""Быстрый переход «Портал» из главного меню — важные этажи башни (список расширяется по балансу)."""

from __future__ import annotations

# Этажи с хабами / вехами; игрок может перейти только если highest_floor_reached >= этажа.
PORTAL_DESTINATION_FLOORS: tuple[int, ...] = (3, 8, 10)
