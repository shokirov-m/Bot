"""Редкости и общие URL заглушек для картинок (UI / item_data)."""

from __future__ import annotations

# Единая заглушка для предметов и для экранов, где нет своего файла (HTTPS для Telegram).
UI_PLACEHOLDER_IMAGE_URL: str = "https://picsum.photos/seed/tower-gear/480/360"
ITEM_IMAGE_PLACEHOLDER_URL: str = UI_PLACEHOLDER_IMAGE_URL

RARITY_EMOJI: dict[str, str] = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🌟",
    "mythic": "✴️",
}

RARITY_NAME_RU: dict[str, str] = {
    "common": "Обычный",
    "uncommon": "Необычный",
    "rare": "Редкий",
    "epic": "Эпический",
    "legendary": "Легендарный",
    "mythic": "Мифический",
}

SECRET_GEAR_MAX_FLOOR = 100
SECRET_GEAR_DROP_CHANCE = min(0.95, 0.55 * 1.2)
SECRET_GEAR_EARLY_MAX_FLOOR = 3
