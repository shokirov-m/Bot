"""
Хаб-локации башни: библиотека (9001), города на полуэтажах (1000+якорь: 0.5, 30.5, …).
"""

from __future__ import annotations

from db.models.character import Character
from game.tower.progression import floor_data

LIBRARY_HUB_FLOOR = 9001
CITY_HUB_FLOOR_BASE = 1000
LEGACY_CITY_HUB_FLOOR_BASE = 9100

_TOWER_RETURN_FLOOR_META = "hub_return_floor_v1"


def city_hub_floor(anchor: int) -> int:
    """Боевой якорь города (0/30/60/90) → этаж внутри башни (1000, 1030, …)."""
    return CITY_HUB_FLOOR_BASE + int(anchor)


def legacy_city_hub_floor(anchor: int) -> int:
    return LEGACY_CITY_HUB_FLOOR_BASE + int(anchor)


def _anchor_from_encoded_hub(n: int, base: int) -> int | None:
    anchor = int(n) - int(base)
    if anchor in floor_data.CITIES:
        return anchor
    return None


def city_anchor_from_hub_floor(floor_number: int) -> int | None:
    n = int(floor_number)
    for base in (CITY_HUB_FLOOR_BASE, LEGACY_CITY_HUB_FLOOR_BASE):
        if n < base or n >= base + 200:
            continue
        return _anchor_from_encoded_hub(n, base)
    return None


def is_library_hub_floor(floor_number: int) -> bool:
    return int(floor_number) == LIBRARY_HUB_FLOOR


def is_city_hub_floor(floor_number: int) -> bool:
    return city_anchor_from_hub_floor(floor_number) is not None


def is_hub_floor(floor_number: int) -> bool:
    return is_library_hub_floor(floor_number) or is_city_hub_floor(floor_number)


def canonical_city_hub_floor(floor_number: int) -> int | None:
    """Канонический номер города в башне (1000+) или None."""
    anchor = city_anchor_from_hub_floor(floor_number)
    if anchor is None:
        return None
    return city_hub_floor(anchor)


def migrate_legacy_city_hub_floor(character: Character) -> bool:
    """91xx → 10xx в сохранении персонажа."""
    n = int(character.floor_number)
    if n < LEGACY_CITY_HUB_FLOOR_BASE or n >= LEGACY_CITY_HUB_FLOOR_BASE + 200:
        return False
    anchor = _anchor_from_encoded_hub(n, LEGACY_CITY_HUB_FLOOR_BASE)
    if anchor is None:
        return False
    character.floor_number = city_hub_floor(anchor)
    return True


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
    canonical = canonical_city_hub_floor(n)
    if canonical is not None:
        n = canonical
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


def peek_return_tower_floor(character: Character) -> int:
    """Боевой этаж, с которого ушли в хаб (без pop)."""
    mp = dict(character.meta_progress or {})
    raw = mp.get(_TOWER_RETURN_FLOOR_META)
    if raw is not None:
        try:
            n = int(raw)
        except (TypeError, ValueError):
            n = 1
        else:
            return max(1, min(n, int(character.highest_floor_reached)))
    hi = int(character.highest_floor_reached)
    if is_city_hub_floor(int(character.floor_number)):
        return max(1, min(hi, 2 if hi >= 2 else 1))
    return max(1, min(hi, int(character.floor_number)))


def pop_return_tower_floor(character: Character) -> int:
    mp = dict(character.meta_progress or {})
    raw = mp.pop(_TOWER_RETURN_FLOOR_META, None)
    if raw is None:
        return peek_return_tower_floor(character)
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = 1
    return max(1, min(n, int(character.highest_floor_reached)))


def player_location_label(floor_number: int) -> str:
    """Подпись локации без технических номеров хабов."""
    n = int(floor_number)
    if is_library_hub_floor(n):
        return "Библиотека гримуаров"
    if is_city_hub_floor(n):
        city = city_for_hub_floor(n)
        if city:
            return f"{city.emoji} {city.name}"
        return "Город"
    return f"Этаж {n}"


def resolve_city_anchor_for_character(character: Character) -> int | None:
    """Якорь города для кузницы/таверны (боевой этаж или город в башне)."""
    if is_city_hub_floor(int(character.floor_number)):
        return city_anchor_from_hub_floor(int(character.floor_number))
    city = floor_data.get_city_for_floor(
        int(character.floor_number),
        highest_reached=int(character.highest_floor_reached),
    )
    return int(city.after_floor) if city else None


def is_quiet_brook_city(character: Character) -> bool:
    """Стартовый город (Тихий Ручей): хаб 0.5 или устаревший боевой этаж 1."""
    n = int(character.floor_number)
    if is_city_hub_floor(n):
        return city_anchor_from_hub_floor(n) == 0
    return n == 1
