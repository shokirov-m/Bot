"""Пути к изображениям в ``content/assets/game_art/`` (меню, NPC, бойцы колизея).

Если файла нет — возвращается ``None`` (экран без баннера). Замените PNG своими, сохранив имена.
"""

from __future__ import annotations

from pathlib import Path

from game.core import paths as content_paths

_ROOT = content_paths.game_art_root()
_LEGACY_UI = content_paths.ui_assets_root()


def _png(rel: str) -> str | None:
    p = _ROOT / rel
    return str(p) if p.is_file() else None


# --- Главное меню и хабы ---


def menu_locations_photo_path() -> str | None:
    return _png("menus/locations.png")


def menu_quests_photo_path() -> str | None:
    return _png("menus/quests.png")


def menu_daily_photo_path() -> str | None:
    return _png("menus/daily.png")


def menu_portal_photo_path() -> str | None:
    return _png("menus/portal.png")


def menu_leaderboard_photo_path() -> str | None:
    return _png("menus/leaderboard.png")


def menu_auction_photo_path() -> str | None:
    return _png("menus/auction.png")


def menu_titles_photo_path() -> str | None:
    return _png("menus/titles.png")


def menu_clan_photo_path() -> str | None:
    return _png("menus/clan.png")


def menu_city_photo_path() -> str | None:
    return _png("menus/city.png")


def menu_arena_photo_path() -> str | None:
    return _png("menus/arena.png")


def menu_settings_photo_path() -> str | None:
    return _png("menus/settings.png")


def menu_shop_photo_path() -> str | None:
    return _png("menus/shop.png")


def menu_shop_vip_photo_path() -> str | None:
    return _png("menus/shop_vip.png")


def menu_workshop_photo_path() -> str | None:
    return _png("menus/workshop.png")


def menu_workshop_orders_photo_path() -> str | None:
    """Городские заказы мастерской (этаж)."""
    return _png("menus/workshop_orders.png")


def menu_home_photo_path() -> str | None:
    """Экран «Дом» и связанные разделы (кроме превью портрета)."""
    return _png("menus/home.png")


def menu_home_wardrobe_photo_path() -> str | None:
    return _png("menus/home_wardrobe.png")


def menu_home_library_photo_path() -> str | None:
    return _png("menus/home_library.png")


# --- Библиотека гримуаров (хаб, не боевой этаж) ---

_LIBRARY_CLASS_KEYS: tuple[str, ...] = (
    "warrior",
    "mage",
    "scout",
    "acolyte",
    "necromancer",
)


def library_hub_photo_path() -> str | None:
    """Зал библиотеки: ``library/grimoire_library.png`` или ``menus/home_library.png``."""
    p = _png("library/grimoire_library.png")
    if p is not None:
        return p
    return menu_home_library_photo_path()


def library_class_photo_path(archetype_key: str) -> str | None:
    """
    Баннер каталога класса: ``library/class_<archetype>.png``.

    warrior · mage · scout · acolyte · necromancer
    """
    raw = (archetype_key or "").strip().lower()
    if raw not in _LIBRARY_CLASS_KEYS:
        return None
    return _png(f"library/class_{raw}.png")


# --- Колизей ---


def coliseum_hub_photo_path() -> str | None:
    """Главный экран колизея: ``menus/coliseum.png`` или старый ``assets/ui/coliseum_menu.png``."""
    p = _png("menus/coliseum.png")
    if p is not None:
        return p
    leg = _LEGACY_UI / "coliseum_menu.png"
    return str(leg) if leg.is_file() else None


def coliseum_fighter_photo_path(fighter_id: int) -> str | None:
    """Портрет бойца по номеру 1…50: ``coliseum/fighters/<n>.png``."""
    n = int(fighter_id)
    if n < 1 or n > 99:
        return None
    return _png(f"coliseum/fighters/{n}.png")


# --- NPC (диалоги, город, квесты) — подставьте свой ключ в имя файла ---


def npc_photo_path(key: str) -> str | None:
    """
    ``npc/<key>.png``, key — латиница, цифры, ``_``.

    Примеры: ``scribe``, ``herbalist``, ``tavern_keeper``, ``temple``, ``market``.
    """
    raw = (key or "").strip().lower()
    k = "".join(c for c in raw if c.isalnum() or c in "_-")
    if not k:
        return None
    return _png(f"npc/{k}.png")


# --- Материалы ремесла (гача) ---


def craft_resource_photo_path(resource_id: str) -> str | None:
    """
    Картинка ремесленного материала (гача/крафт):
    ``materials/<resource_id>.png``.
    """
    raw = (resource_id or "").strip().lower()
    rid = "".join(c for c in raw if c.isalnum() or c in "_-")
    if not rid:
        return None
    return _png(f"materials/{rid}.png")
