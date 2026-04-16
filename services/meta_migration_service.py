"""
Одноразовая нормализация meta после разделения званий (path_*) и титулов.
"""

from __future__ import annotations

from db.models.character import Character
from game.characters.path_ranks import PATH_RANK_SPECS

_RANK_NAMES_RU: frozenset[str] = frozenset(spec[1] for spec in PATH_RANK_SPECS)

_MIGRATION_FLAG = "titles_path_migration_v1"
_META_UNLOCKED = "titles_unlocked"


def apply_legacy_title_rank_migration(character: Character) -> None:
    """Удалить path_* из titles_unlocked; сбросить active_title, если это имя звания."""
    mp = dict(character.meta_progress or {})
    if mp.get(_MIGRATION_FLAG):
        character.meta_progress = mp
        return

    raw = mp.get(_META_UNLOCKED)
    if isinstance(raw, list):
        cleaned = [str(x) for x in raw if not str(x).startswith("path_")]
        if len(cleaned) != len(raw):
            mp[_META_UNLOCKED] = cleaned

    at = character.active_title
    if at and str(at) in _RANK_NAMES_RU:
        character.active_title = None

    mp[_MIGRATION_FLAG] = True
    character.meta_progress = mp
