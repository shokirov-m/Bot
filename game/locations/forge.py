"""Доступ к кузнице в городах-хабах (3, 31, 61, 91) и полевая починка на сценарных этажах."""

from __future__ import annotations

from game.floors import floor_data


def forge_available_on_floor(floor_number: int) -> bool:
    return floor_data.get_city_for_floor(floor_number) is not None


def tower_field_repair_allowed(floor_number: int) -> bool:
    """
    Починка за золото с карты этажа (не заходя в город): комнаты, волны, исследования.
    Тарифы и логика — те же, что в городской кузнице (forge_service).
    """
    n = int(floor_number)
    from game.floors import explore_floor as exp8
    from game.floors import explore_floor_22 as exp22
    from game.floors import explore_floor_4 as exp4
    from game.floors import room_clear_floor as rc5
    from game.floors import room_clear_floor_10 as rc10
    from game.floors import room_clear_floor_24 as rc24
    from game.floors import room_clear_floor_26 as rc26
    from game.floors import room_clear_floor_30 as rc30
    from game.floors import room_clear_floor_40 as rc40
    from game.floors import wave_floor as wv
    from game.floors import wave_floor_27 as wv27

    if exp4.is_explore_floor_4(n):
        return True
    if exp8.is_explore_floor(n):
        return True
    if exp22.is_explore_floor_22(n):
        return True
    if rc5.is_room_clear_floor(n):
        return True
    if rc10.is_room_clear_floor_10(n):
        return True
    if rc24.is_room_clear_floor_24(n):
        return True
    if rc30.is_room_clear_floor_30(n):
        return True
    if rc40.is_room_clear_floor_40(n):
        return True
    if rc26.is_room_clear_floor_26(n):
        return True
    if wv27.is_wave_floor_27(n):
        return True
    if wv.is_wave_floor(n) and not rc10.is_room_clear_floor_10(n):
        return True
    return False


def repair_allowed_on_floor(floor_number: int) -> bool:
    """Починка: в городе-хабе или на полевых сценарных этажах."""
    return forge_available_on_floor(floor_number) or tower_field_repair_allowed(floor_number)
