"""
Пути к PNG: локации, монстры, предметы.

Корень ассетов: ``game.core.paths.assets_root()`` (``content/assets/``).
"""

from __future__ import annotations

from pathlib import Path

from game.core import paths as content_paths
from game.tower.progression import floor_data

# Явный путь, если файл назван иначе (редко). Относительно корня tower_bot.
_BATTLE_PORTRAIT_OVERRIDES: dict[str, str] = {
    "golden_goblin": content_paths.rel_assets("monsters", "rotten_swamps", "golden.png"),
    "mimic_chest": content_paths.rel_assets("images", "treasure", "chest_mimic.png"),
    # Мини-босс болот (этаж 15): тот же арт, что у карточки короля слизней.
    "mini_bog_queen": content_paths.rel_assets("monsters", "rotten_swamps", "boss_slime_king.png"),
    # Мажор болот (этаж 20): файл спрайта называется snake.png.
    "boss_slime_king": content_paths.rel_assets("monsters", "rotten_swamps", "snake.png"),
}

# «elite_» = 6 символов; срез [7:] ломал ключ (elite_orc → «rc») и портрет/каталог.
_ELITE_PREFIX = "elite_"


def tower_bot_root() -> Path:
    """Корень пакета tower_bot."""
    return content_paths.tower_bot_root()


def item_images_dir() -> Path:
    return content_paths.items_root()


def item_gear_png(stem: str) -> str:
    """Путь к ``content/assets/items/{stem}.png`` (для ``image_url`` в item_data)."""
    return content_paths.rel_assets("items", f"{stem}.png")


def item_gear_png_rarity(stem: str, rarity: str) -> str:
    """Путь к ``content/assets/items/{rarity}/{stem}.png``."""
    return content_paths.rel_assets("items", rarity, f"{stem}.png")


def procedural_secret_gear_image(kind: str) -> str:
    """Тайник на высоких этажах: одна заглушка на вид экипировки."""
    k = (kind or "armor").lower()
    return item_gear_png(f"proc_secret_{k}")


def assets_images_root() -> Path:
    return content_paths.images_root()


def location_image_for_floor(floor_number: int) -> Path | None:
    """
    Картинка фона этажа.

    Приоритет:
    0. Хабы (библиотека 9001, города 91xx) — отдельные арты, не зона этажа 99.
    1. `locations/floor_{N}.png` — свой фон для конкретного этажа (например 1–3).
    2. `locations/{zone.key}.png` — картинка зоны из `floor_data`.
    3. `locations/default.png`.
    """
    n = int(floor_number)
    from game.locations import hub_floors as hf
    from utils.media import game_art as ga

    if hf.is_library_hub_floor(n):
        p = ga.library_hub_photo_path()
        if p:
            return Path(p)
    if hf.is_city_hub_floor(n):
        p = ga.menu_city_photo_path()
        if p:
            return Path(p)
    loc_dir = assets_images_root() / "locations"
    per_floor = loc_dir / f"floor_{n}.png"
    if per_floor.is_file():
        return per_floor
    zone = floor_data.get_zone_for_floor(n)
    for name in (f"{zone.key}.png", "default.png"):
        p = loc_dir / name
        if p.is_file():
            return p
    return None


def secret_chest_png(kind: str) -> str | None:
    """PNG тайника: closed / empty / gold / mimic → ``chest_{kind}.png`` (mimic → ``chest_mimic.png``)."""
    k = (kind or "closed").lower().strip()
    if k == "mimic":
        p = assets_images_root() / "treasure" / "chest_mimic.png"
        return str(p) if p.is_file() else None
    if k not in ("closed", "empty", "gold"):
        k = "closed"
    p = assets_images_root() / "treasure" / f"chest_{k}.png"
    return str(p) if p.is_file() else None


def _monster_png_resolved(
    template_key: str,
    *,
    default_fallback: bool,
    zone_key: str | None = None,
) -> Path | None:
    k = (template_key or "").strip()
    if not k:
        return None
    root = tower_bot_root()
    rel_ov = _BATTLE_PORTRAIT_OVERRIDES.get(k)
    if rel_ov:
        p = root / rel_ov
        if p.is_file():
            return p
    base_k = k[len(_ELITE_PREFIX) :] if k.startswith(_ELITE_PREFIX) else k
    mon_dir = content_paths.monsters_root()
    if zone_key:
        zk = (zone_key or "").strip()
        if zk:
            zdir = mon_dir / zk
            for cand in (k, base_k):
                p = zdir / f"{cand}.png"
                if p.is_file():
                    return p
    for cand in (k, base_k):
        p = mon_dir / f"{cand}.png"
        if p.is_file():
            return p
    if default_fallback:
        d = mon_dir / "default.png"
        return d if d.is_file() else None
    return None


def monster_image_for_template(template_key: str, *, zone_key: str | None = None) -> Path | None:
    """Картинка монстра для UI; при отсутствии файла — ``default.png``, если есть."""
    return _monster_png_resolved(template_key, default_fallback=True, zone_key=zone_key)


def combat_monster_portrait_path(template_key: str, *, floor_number: int | None = None) -> str | None:
    """PNG для экрана боя — только если файл существует (без подстановки default)."""
    zone_key: str | None = None
    if floor_number is not None:
        try:
            zone_key = floor_data.get_zone_for_floor(int(floor_number)).key
        except Exception:
            zone_key = None
    p = _monster_png_resolved(template_key, default_fallback=False, zone_key=zone_key)
    return str(p) if p is not None else None


def item_image_default() -> Path | None:
    """Заглушка предмета — под инвентарь / карточки."""
    p = assets_images_root() / "items" / "default.png"
    return p if p.is_file() else None
