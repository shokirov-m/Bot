"""
Пути к картинкам для UI (этажи, монстры, предметы).

Файлы лежат в `tower_bot/assets/images/`. Подменяй PNG своими — имена см. README в папке.
"""

from __future__ import annotations

from pathlib import Path

from game.floors import floor_data

_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "images"


def assets_images_root() -> Path:
    return _ASSETS


def location_image_for_floor(floor_number: int) -> Path | None:
    """
    Картинка фона этажа.

    Приоритет:
    1. `locations/floor_{N}.png` — свой фон для конкретного этажа (например 1–3).
    2. `locations/{zone.key}.png` — картинка зоны из `floor_data`.
    3. `locations/default.png`.
    """
    n = int(floor_number)
    loc_dir = _ASSETS / "locations"
    per_floor = loc_dir / f"floor_{n}.png"
    if per_floor.is_file():
        return per_floor
    zone = floor_data.get_zone_for_floor(n)
    for name in (f"{zone.key}.png", "default.png"):
        p = loc_dir / name
        if p.is_file():
            return p
    return None


def monster_image_for_template(template_key: str) -> Path | None:
    """`monsters/{key}.png` — для будущего UI боя; сейчас чаще только default."""
    key = (template_key or "").strip().lower().replace(" ", "_")
    mon_dir = _ASSETS / "monsters"
    if key:
        p = mon_dir / f"{key}.png"
        if p.is_file():
            return p
    d = mon_dir / "default.png"
    return d if d.is_file() else None


def item_image_default() -> Path | None:
    """Заглушка предмета — под инвентарь / карточки."""
    p = _ASSETS / "items" / "default.png"
    return p if p.is_file() else None
