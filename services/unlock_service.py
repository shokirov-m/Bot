"""
Progressive unlocks for new players (UI gating + one-time notifications).

State is stored in character.meta_progress['unlocks_v1'].
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from db.models.character import Character

META_KEY = "unlocks_v1"


@dataclass(frozen=True, slots=True)
class Unlock:
    key: str
    level: int
    title: str
    hint: str


# Keys are used by keyboards/handlers.
UNLOCKS: tuple[Unlock, ...] = (
    Unlock(
        key="menu_locations",
        level=5,
        title="Локации",
        hint="Меню → Локации (там: мастерская и другие режимы).",
    ),
    Unlock(
        key="menu_workshop",
        level=5,
        title="Мастерская",
        hint="Меню → Локации → Мастерская.",
    ),
    Unlock(
        key="menu_quests",
        level=6,
        title="Квесты",
        hint="Меню → Квесты.",
    ),
    Unlock(
        key="menu_top",
        level=7,
        title="Топ игроков",
        hint="Меню → Топ игроков.",
    ),
    Unlock(
        key="menu_home",
        level=8,
        title="Дом",
        hint="Меню → Дом (бонусы и доступ к верстаку).",
    ),
    Unlock(
        key="menu_portal",
        level=9,
        title="Портал",
        hint="Меню → Портал (быстрые переходы).",
    ),
    Unlock(
        key="menu_settings",
        level=10,
        title="Настройки",
        hint="Меню → Настройки.",
    ),
    Unlock(
        key="menu_arena",
        level=10,
        title="Арена",
        hint="Меню → Локации → Арена.",
    ),
    Unlock(
        key="menu_coliseum",
        level=10,
        title="Колизей",
        hint="Меню → Локации → Колизей.",
    ),
    Unlock(
        key="menu_auction",
        level=10,
        title="Аукцион",
        hint="Меню → Локации → Аукцион.",
    ),
    Unlock(
        key="menu_clan",
        level=10,
        title="Клан",
        hint="Меню → Локации → Клан.",
    ),
)

UNLOCK_BY_KEY: dict[str, Unlock] = {u.key: u for u in UNLOCKS}


def _slot(meta: dict[str, Any]) -> dict[str, Any]:
    raw = meta.get(META_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def is_unlocked(character: Character, key: str) -> bool:
    u = UNLOCK_BY_KEY.get(key)
    if u is None:
        return True
    return int(character.level or 1) >= int(u.level)


def available_main_menu_keys(character: Character) -> set[str]:
    """
    Which main menu sections are visible.

    Up to level 4: profile, floor, inventory only (per user request).
    """
    base = {"menu_profile", "menu_floor", "menu_inv"}
    lv = int(character.level or 1)
    if lv < 5:
        return base
    keys = set(base)
    for u in UNLOCKS:
        if lv >= int(u.level):
            keys.add(u.key)
    return keys


def available_locations_menu_keys(character: Character) -> set[str]:
    """
    Which sub-items inside Locations hub are visible.
    Before level 5, Locations hub is hidden entirely.
    """
    lv = int(character.level or 1)
    if lv < 5:
        return set()
    keys: set[str] = set()
    for u in UNLOCKS:
        if u.key.startswith("menu_") and lv >= int(u.level):
            keys.add(u.key)
    return keys


def collect_level_unlock_notifications(character: Character, *, old_level: int, new_level: int) -> list[str]:
    """
    Returns list of HTML lines to notify player about newly unlocked features.
    Marks them as 'notified' inside meta_progress so they won't repeat.
    """
    old_lv = int(old_level)
    new_lv = int(new_level)
    if new_lv <= old_lv:
        return []
    meta = dict(character.meta_progress or {})
    st = _slot(meta)
    notified = set(st.get("notified", []) or [])
    out: list[str] = []
    for u in UNLOCKS:
        if old_lv < int(u.level) <= new_lv and u.key not in notified:
            out.append(f"🔓 <b>Открылось:</b> {u.title}\n<i>{u.hint}</i>")
            notified.add(u.key)
    if out:
        st["notified"] = sorted(str(x) for x in notified)
        meta[META_KEY] = st
        character.meta_progress = meta
        try:
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(character, "meta_progress")
        except Exception:
            pass
    return out

