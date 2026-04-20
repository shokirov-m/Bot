"""
Пути к PNG: локации, монстры, предметы.

Файлы экипировки — ``tower_bot/assets/items/{stem}.png`` (item_gear_png).
Монстры — ``tower_bot/assets/monsters/{key}.png``.
"""

from __future__ import annotations

from pathlib import Path

from game.floors import floor_data

# Явный путь, если файл назван иначе (редко).
_BATTLE_PORTRAIT_OVERRIDES: dict[str, str] = {
    "golden_goblin": "assets/monsters/golden.png",
}


def tower_bot_root() -> Path:
    """Корень пакета tower_bot."""
    return Path(__file__).resolve().parent.parent


def item_images_dir() -> Path:
    return tower_bot_root() / "assets" / "items"


def item_gear_png(stem: str) -> str:
    """Путь к ``assets/items/{stem}.png`` (для ``image_url`` в item_data)."""
    return str(item_images_dir() / f"{stem}.png")


def procedural_secret_gear_image(kind: str) -> str:
    """Тайник на высоких этажах: одна заглушка на вид экипировки."""
    k = (kind or "armor").lower()
    return item_gear_png(f"proc_secret_{k}")


_ASSETS_IMAGES = tower_bot_root() / "assets" / "images"


def assets_images_root() -> Path:
    return _ASSETS_IMAGES


def location_image_for_floor(floor_number: int) -> Path | None:
    """
    Картинка фона этажа.

    Приоритет:
    1. `locations/floor_{N}.png` — свой фон для конкретного этажа (например 1–3).
    2. `locations/{zone.key}.png` — картинка зоны из `floor_data`.
    3. `locations/default.png`.
    """
    n = int(floor_number)
    loc_dir = _ASSETS_IMAGES / "locations"
    per_floor = loc_dir / f"floor_{n}.png"
    if per_floor.is_file():
        return per_floor
    zone = floor_data.get_zone_for_floor(n)
    for name in (f"{zone.key}.png", "default.png"):
        p = loc_dir / name
        if p.is_file():
            return p
    return None


def _monster_png_resolved(template_key: str, *, default_fallback: bool) -> Path | None:
    k = (template_key or "").strip()
    if not k:
        return None
    root = tower_bot_root()
    rel_ov = _BATTLE_PORTRAIT_OVERRIDES.get(k)
    if rel_ov:
        p = root / rel_ov
        if p.is_file():
            return p
    base_k = k[7:] if k.startswith("elite_") else k
    mon_dir = root / "assets" / "monsters"
    for cand in (k, base_k):
        p = mon_dir / f"{cand}.png"
        if p.is_file():
            return p
    if default_fallback:
        d = mon_dir / "default.png"
        return d if d.is_file() else None
    return None


def monster_image_for_template(template_key: str) -> Path | None:
    """Картинка монстра для UI; при отсутствии файла — ``default.png``, если есть."""
    return _monster_png_resolved(template_key, default_fallback=True)


def combat_monster_portrait_path(template_key: str) -> str | None:
    """PNG для экрана боя — только если файл существует (без подстановки default)."""
    p = _monster_png_resolved(template_key, default_fallback=False)
    return str(p) if p is not None else None


def item_image_default() -> Path | None:
    """Заглушка предмета — под инвентарь / карточки."""
    p = _ASSETS_IMAGES / "items" / "default.png"
    return p if p.is_file() else None
