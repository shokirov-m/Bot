"""
Разблокировка титулов (meta_progress.titles_unlocked) и смена active_title (+ второй слот в meta).
"""

from __future__ import annotations

from db.models.character import Character
from game.characters.titles import ALL_TITLES, TITLE_BY_KEY

_META_UNLOCKED = "titles_unlocked"
_META_SECONDARY_TITLE = "active_title_secondary_name_ru"


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


def _name_ru_for_secondary(character: Character) -> str | None:
    raw = (character.meta_progress or {}).get(_META_SECONDARY_TITLE)
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def active_secondary_title_key(character: Character) -> str | None:
    """Второй активный титул (имя в meta, как у основного)."""
    at = _name_ru_for_secondary(character)
    if not at:
        return None
    for tt in ALL_TITLES:
        if tt.name_ru == at:
            return tt.key
    return None


def equip(character: Character, key: str, *, slot: int = 1) -> tuple[bool, str]:
    """slot 1 — колонка active_title; slot 2 — meta active_title_secondary_name_ru."""
    refresh_unlocks(character)
    if key not in set(_unlocked_list(character)):
        return False, "Титул ещё не открыт."
    td = TITLE_BY_KEY.get(key)
    if td is None:
        return False, "Неизвестный титул."
    if slot == 1 and active_secondary_title_key(character) == key:
        return False, "Этот титул уже во втором слоте."
    if slot == 2 and active_title_key(character) == key:
        return False, "Этот титул уже в первом слоте."
    if slot == 2:
        mp = dict(character.meta_progress or {})
        mp[_META_SECONDARY_TITLE] = td.name_ru
        character.meta_progress = mp
        return True, td.name_ru
    character.active_title = td.name_ru
    return True, td.name_ru


def clear_active(character: Character, *, slot: int | None = None) -> None:
    """slot None — снять оба; 1 — только основной; 2 — только второй."""
    if slot is None or slot == 1:
        character.active_title = None
    if slot is None or slot == 2:
        mp = dict(character.meta_progress or {})
        if _META_SECONDARY_TITLE in mp:
            del mp[_META_SECONDARY_TITLE]
            character.meta_progress = mp


def active_title_key(character: Character) -> str | None:
    """Ключ титула по строке в профиле (active_title хранит name_ru)."""
    at = character.active_title
    if not at:
        return None
    for tt in ALL_TITLES:
        if tt.name_ru == at:
            return tt.key
    return None


def reward_bonus_multipliers(character: Character) -> tuple[float, float]:
    """Множители (золото, опыт) за победу — оба слота титула перемножаются."""
    gm, xm = 1.0, 1.0
    for k in (active_title_key(character), active_secondary_title_key(character)):
        if not k:
            continue
        tt = TITLE_BY_KEY.get(k)
        if tt is None:
            continue
        gm *= 1.0 + tt.gold_bonus_pct / 100.0
        xm *= 1.0 + tt.xp_bonus_pct / 100.0
    return gm, xm


def admin_ensure_title_unlocked(character: Character, key: str) -> tuple[bool, str]:
    """Админ: гарантированно добавить ключ в titles_unlocked (даже если уже был)."""
    if key not in TITLE_BY_KEY:
        return False, "Неизвестный ключ титула."
    mp = dict(character.meta_progress or {})
    raw = mp.get(_META_UNLOCKED)
    have: set[str] = set(str(x) for x in raw) if isinstance(raw, list) else set()
    have.add(key)
    mp[_META_UNLOCKED] = sorted(have)
    character.meta_progress = mp
    td = TITLE_BY_KEY[key]
    return True, td.name_ru


def grant_title_key(character: Character, key: str, *, silent: bool = False) -> bool:
    """
    Выдать титул по ключу (для наград квестов/Колизея): дописать в meta_progress.titles_unlocked.
    Возвращает True, если ключ был новым. silent — без лишних побочек (тосты зовут refresh сами).
    """
    if key not in TITLE_BY_KEY:
        return False
    mp = dict(character.meta_progress or {})
    raw = mp.get(_META_UNLOCKED)
    have: set[str] = set(str(x) for x in raw) if isinstance(raw, list) else set()
    if key in have:
        return False
    have.add(key)
    mp[_META_UNLOCKED] = sorted(have)
    character.meta_progress = mp
    if not silent:
        refresh_unlocks(character)
    return True
