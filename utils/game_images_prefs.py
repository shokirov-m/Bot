"""
Фон этажа и портрет в профиле: общий флаг в meta_progress персонажа.
"""

from __future__ import annotations

from db.models.character import Character

META_HIDE_GAME_IMAGES = "hide_game_images"


def game_images_enabled(character: Character) -> bool:
    """По умолчанию картинки включены."""
    mp = character.meta_progress or {}
    return not bool(mp.get(META_HIDE_GAME_IMAGES))


def set_game_images_hidden(character: Character, hide: bool) -> None:
    mp = dict(character.meta_progress or {})
    if hide:
        mp[META_HIDE_GAME_IMAGES] = True
    else:
        mp.pop(META_HIDE_GAME_IMAGES, None)
    character.meta_progress = mp
