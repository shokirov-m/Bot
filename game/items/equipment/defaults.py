"""Поля по умолчанию для JSON предмета (картинка-заглушка)."""

from __future__ import annotations

from typing import Any

from game.items.equipment.constants import ITEM_IMAGE_PLACEHOLDER_URL


def apply_item_payload_defaults(data: dict[str, Any]) -> dict[str, Any]:
    """Дописать в item_data отсутствующие визуальные поля (на месте — не перезаписываем)."""
    if not data.get("image_url"):
        data["image_url"] = str(ITEM_IMAGE_PLACEHOLDER_URL)
    return data
