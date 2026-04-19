"""Поля по умолчанию для JSON предмета (картинка-заглушка)."""

from __future__ import annotations

from typing import Any

from utils.image_assets import item_gear_png


def apply_item_payload_defaults(data: dict[str, Any]) -> dict[str, Any]:
    """Дописать в item_data отсутствующие визуальные поля (на месте — не перезаписываем)."""
    if not data.get("image_url"):
        data["image_url"] = item_gear_png("placeholder_item")
    return data
