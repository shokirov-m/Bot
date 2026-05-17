"""Пути к статичным UI-изображениям (меню инвентаря, специализация)."""

from __future__ import annotations

from game.core import paths as content_paths


def inventory_menu_photo_path() -> str | None:
    """Фон главного экрана сумки (`content/assets/ui/inventory_menu.png`)."""
    p = content_paths.ui_assets_root() / "inventory_menu.png"
    return str(p) if p.is_file() else None


def specialization_menu_photo_path() -> str | None:
    """Фон раздела «Специализация» (`content/assets/ui/specialization_menu.png`)."""
    p = content_paths.ui_assets_root() / "specialization_menu.png"
    return str(p) if p.is_file() else None
