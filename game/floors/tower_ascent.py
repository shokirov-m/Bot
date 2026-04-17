"""Ручной подъём на следующий этаж после зачистки (meta_progress)."""

from __future__ import annotations

from db.models.character import Character

META_TOWER_ASCENT_PENDING = "tower_ascent_pending"


def tower_next_floor_pending(character: Character) -> int | None:
    """Следующий этаж, на который можно подняться с текущего (если зачистка завершена)."""
    mp = character.meta_progress or {}
    raw = mp.get(META_TOWER_ASCENT_PENDING)
    if raw is None:
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    cur = int(character.floor_number)
    if n == cur + 1:
        return n
    return None


def set_tower_ascent_pending(character: Character, next_floor: int) -> None:
    mp = dict(character.meta_progress or {})
    mp[META_TOWER_ASCENT_PENDING] = int(next_floor)
    character.meta_progress = mp


def clear_tower_ascent_pending(character: Character) -> None:
    mp = dict(character.meta_progress or {})
    if META_TOWER_ASCENT_PENDING not in mp:
        return
    mp.pop(META_TOWER_ASCENT_PENDING, None)
    character.meta_progress = mp


def is_peaceful_city_hub_floor(floor_number: int) -> bool:
    """Этажи без боёв на карте — только хаб (сейчас этаж 3)."""
    return int(floor_number) == 3


def ensure_peaceful_city_hub_ascent(character: Character) -> bool:
    """
    На мирном хабе сразу можно подняться на следующий этаж (без зачистки целей).
    Возвращает True, если в meta_progress появился или подтверждён флаг подъёма.
    """
    if not is_peaceful_city_hub_floor(int(character.floor_number)):
        return False
    from game.floors.monsters import build_spawns_for_floor

    if build_spawns_for_floor(3):
        return False
    cur = int(character.floor_number)
    if cur >= 100:
        return False
    nxt = cur + 1
    if tower_next_floor_pending(character) == nxt:
        # Всё ещё обновим highest, чтобы можно было зайти на следующий ярус без боя.
        hi = int(character.highest_floor_reached)
        if hi < nxt:
            character.highest_floor_reached = nxt
        return hi < nxt
    set_tower_ascent_pending(character, nxt)
    hi = int(character.highest_floor_reached)
    if hi < nxt:
        character.highest_floor_reached = nxt
    return True
