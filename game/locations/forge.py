"""Доступ к кузнице в городах-хабах (3, 31, 61, 91) и полевая починка на сценарных этажах."""

from __future__ import annotations

from game.tower.progression import floor_data


def forge_available_on_floor(floor_number: int) -> bool:
    return floor_data.get_city_for_floor(floor_number) is not None


def tower_field_repair_allowed(floor_number: int) -> bool:
    """
    Починка за золото с карты этажа (не заходя в город): комнаты, волны, исследования.
    Тарифы и логика — те же, что в городской кузнице (forge_service).
    """
    from game.tower.mechanics import registry as mech

    return mech.tower_field_repair_allowed(floor_number)


def repair_allowed_on_floor(floor_number: int) -> bool:
    """Починка: в городе-хабе или на полевых сценарных этажах."""
    return forge_available_on_floor(floor_number) or tower_field_repair_allowed(floor_number)
