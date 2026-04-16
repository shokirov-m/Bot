"""
Разблокировка титулов (meta_progress.titles_unlocked) и смена active_title.
"""

from __future__ import annotations

from db.models.character import Character
from game.characters.titles import ALL_TITLES, TITLE_BY_KEY

_META_UNLOCKED = "titles_unlocked"


def _unlocked_list(character: Character) -> list[str]:
    raw = (character.meta_progress or {}).get(_META_UNLOCKED)
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def refresh_unlocks(character: Character) -> list[str]:
    """
    Проверить условия и дописать новые ключи в meta_progress.
    Возвращает список только что открытых ключей (для тоста в бою).
    """
    mp = dict(character.meta_progress or {})
    unlocked = set(_unlocked_list(character))
    new_keys: list[str] = []
    for t in ALL_TITLES:
        if t.key in unlocked:
            continue
        if t.check(character):
            unlocked.add(t.key)
            new_keys.append(t.key)
    if new_keys:
        mp[_META_UNLOCKED] = sorted(unlocked)
        character.meta_progress = mp
    return new_keys


def unlocked_sorted(character: Character) -> list[str]:
    """Ключи открытых титулов по порядку сортировки в реестре."""
    have = set(_unlocked_list(character))
    return [t.key for t in ALL_TITLES if t.key in have]


def display_names(keys: list[str]) -> list[str]:
    return [TITLE_BY_KEY[k].name_ru for k in keys if k in TITLE_BY_KEY]


def equip(character: Character, key: str) -> tuple[bool, str]:
    refresh_unlocks(character)
    if key not in set(_unlocked_list(character)):
        return False, "Титул ещё не открыт."
    t = TITLE_BY_KEY.get(key)
    if t is None:
        return False, "Неизвестный титул."
    character.active_title = t.name_ru
    return True, t.name_ru


def clear_active(character: Character) -> None:
    character.active_title = None


def active_title_key(character: Character) -> str | None:
    """Ключ титула по строке в профиле (active_title хранит name_ru)."""
    at = character.active_title
    if not at:
        return None
    for t in ALL_TITLES:
        if t.name_ru == at:
            return t.key
    return None


def reward_bonus_multipliers(character: Character) -> tuple[float, float]:
    """Множители (золото, опыт) за победу, если выбран активный титул."""
    k = active_title_key(character)
    if not k:
        return 1.0, 1.0
    t = TITLE_BY_KEY.get(k)
    if t is None:
        return 1.0, 1.0
    gm = 1.0 + t.gold_bonus_pct / 100.0
    xm = 1.0 + t.xp_bonus_pct / 100.0
    return gm, xm
