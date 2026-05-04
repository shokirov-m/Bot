"""Пути к статичным UI-изображениям (меню инвентаря, специализация)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent


def inventory_menu_photo_path() -> str | None:
    """Фон главного экрана сумки (`assets/ui/inventory_menu.png`)."""
    p = _ROOT / "assets" / "ui" / "inventory_menu.png"
    return str(p) if p.is_file() else None


def specialization_menu_photo_path() -> str | None:
    """Фон раздела «Специализация» и подэкранов (`assets/ui/specialization_menu.png`)."""
    p = _ROOT / "assets" / "ui" / "specialization_menu.png"
    return str(p) if p.is_file() else None
