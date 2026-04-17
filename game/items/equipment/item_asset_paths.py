"""
Абсолютные пути к PNG предметов в ``tower_bot/assets/items/``.
Замените файл с тем же именем — бот отправит локальное фото через FSInputFile.
"""

from __future__ import annotations

from pathlib import Path


def tower_bot_root() -> Path:
    """Корень пакета ``tower_bot`` (родитель ``game``)."""
    return Path(__file__).resolve().parents[3]


def item_images_dir() -> Path:
    return tower_bot_root() / "assets" / "items"


def item_gear_png(stem: str) -> str:
    """Путь к ``assets/items/{stem}.png`` (для ``image_url`` в item_data)."""
    return str(item_images_dir() / f"{stem}.png")


def procedural_secret_gear_image(kind: str) -> str:
    """Тайник на высоких этажах: одна заглушка на вид экипировки."""
    k = (kind or "armor").lower()
    return item_gear_png(f"proc_secret_{k}")
