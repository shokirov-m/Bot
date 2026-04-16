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
