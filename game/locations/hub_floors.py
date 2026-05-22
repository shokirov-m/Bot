"""
Независимые хаб-этажи (не боевые ярусы башни).
9001 — библиотека гримуаров; 9100+якорь — города-хабы.
"""

from __future__ import annotations

from db.models.character import Character
from game.tower.progression import floor_data

LIBRARY_HUB_FLOOR = 9001
CITY_HUB_FLOOR_BASE = 9100

_TOWER_RETURN_FLOOR_META = "hub_return_floor_v1"


def city_hub_floor(anchor: int) -> int:
    return CITY_HUB_FLOOR_BASE + int(anchor)


def is_library_hub_floor(floor_number: int) -> bool:
    return int(floor_number) == LIBRARY_HUB_FLOOR


def is_city_hub_floor(floor_number: int) -> bool:
    n = int(floor_number)
    if n < CITY_HUB_FLOOR_BASE or n >= CITY_HUB_FLOOR_BASE + 200:
        return False
    anchor = n - CITY_HUB_FLOOR_BASE
    return anchor in floor_data.CITIES


def is_hub_floor(floor_number: int) -> bool:
    return is_library_hub_floor(floor_number) or is_city_hub_floor(floor_number)


def city_anchor_from_hub_floor(floor_number: int) -> int | None:
    if not is_city_hub_floor(floor_number):
        return None
    return int(floor_number) - CITY_HUB_FLOOR_BASE


def city_for_hub_floor(floor_number: int):
    anchor = city_anchor_from_hub_floor(floor_number)
    if anchor is None:
        return None
    return floor_data.CITIES.get(anchor)


def library_hub_accessible(character: Character) -> bool:
    from game.locations.grimoire_library import library_unlocked

    return library_unlocked(character)


def city_hub_accessible(character: Character, floor_number: int) -> bool:
    city = city_for_hub_floor(floor_number)
    if city is None:
        return False
    return int(character.highest_floor_reached) > int(city.after_floor)


def can_travel_to_hub_floor(character: Character, target_floor: int) -> bool:
    n = int(target_floor)
    if is_library_hub_floor(n):
        return library_hub_accessible(character)
    if is_city_hub_floor(n):
        return city_hub_accessible(character, n)
    return False


def list_accessible_city_hub_floors(character: Character) -> list[tuple[int, str, str]]:
    hi = int(character.highest_floor_reached)
    out: list[tuple[int, str, str]] = []
    for anchor in sorted(floor_data.CITIES.keys()):
        city = floor_data.CITIES[anchor]
        if hi > int(city.after_floor):
            fl = city_hub_floor(anchor)
            out.append((fl, str(city.emoji), str(city.name)))
    return out


def remember_tower_floor(character: Character) -> None:
    """Запомнить боевой этаж перед уходом в хаб."""
    n = int(character.floor_number)
    if is_hub_floor(n):
        return
    if n < 1:
        return
    mp = dict(character.meta_progress or {})
    mp[_TOWER_RETURN_FLOOR_META] = n
    character.meta_progress = mp


def pop_return_tower_floor(character: Character) -> int:
    mp = dict(character.meta_progress or {})
    raw = mp.pop(_TOWER_RETURN_FLOOR_META, None)
    if raw is None:
        return max(1, min(int(character.highest_floor_reached), int(character.floor_number)))
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = 1
    return max(1, min(n, int(character.highest_floor_reached)))


def player_location_label(floor_number: int) -> str:
    """Подпись локации для игрока (без технических номеров хабов 9001/91xx)."""
    n = int(floor_number)
    if is_library_hub_floor(n):
        return "Библиотека гримуаров"
    if is_city_hub_floor(n):
        city = city_for_hub_floor(n)
        if city:
            return f"{city.emoji} {city.name}"
        return "Город-хаб"
    return f"Этаж {n}"


def resolve_city_anchor_for_character(character: Character) -> int | None:
    """Якорь города для кузницы/таверны (боевой этаж или хаб-этаж города)."""
    if is_city_hub_floor(int(character.floor_number)):
        return city_anchor_from_hub_floor(int(character.floor_number))
    city = floor_data.get_city_for_floor(
        int(character.floor_number),
        highest_reached=int(character.highest_floor_reached),
    )
    return int(city.after_floor) if city else None

