"""
Зоны и города-хабы — сырые dict для game/tower/progression/floor_data.py.
Высота башни неизвестна (этажи 101+ сняты до отдельной переработки).
"""

from __future__ import annotations

from typing import Any

ZONES_RAW: tuple[dict[str, Any], ...] = (
    {
        "key": "forest_beginnings",
        "name": "Лес Начал",
        "emoji": "🌲",
        "floor_from": 1,
        "floor_to": 10,
        "description": "Волки, пауки и гоблины охраняют нижние кольца.",
    },
    {
        "key": "rotten_swamps",
        "name": "Гнилые Болота",
        "emoji": "🌿",
        "floor_from": 11,
        "floor_to": 20,
        "description": (
            "Токсичный туман бьёт по HP перед боями (иммунитет при защите снаряжения 5+); "
            "пиявки заносят яд на следующий этаж; густой туман на карте; заброшенный лагерь — лут или ловушка."
        ),
    },
    {
        "key": "shadow_caves",
        "name": "Пещеры Теней",
        "emoji": "🕳️",
        "floor_from": 21,
        "floor_to": 30,
        "description": "Теневые твари и крылатые тени в темноте.",
    },
    {
        "key": "icy_peaks",
        "name": "Ледяные Пики",
        "emoji": "❄️",
        "floor_from": 31,
        "floor_to": 40,
        "description": "Мороз, големы и снежные йети.",
    },
    {
        "key": "desert_oblivion",
        "name": "Пустыня Забвения",
        "emoji": "🏜️",
        "floor_from": 41,
        "floor_to": 50,
        "description": "Жар, скорпионы и пески, искажающие время.",
    },
    {
        "key": "volcanic_ruins",
        "name": "Вулканические Руины",
        "emoji": "🌋",
        "floor_from": 51,
        "floor_to": 60,
        "description": "Лава, огненные элементали и драконьи тени.",
    },
    {
        "key": "blood_spire",
        "name": "Кровавый Шпиль",
        "emoji": "🦇",
        "floor_from": 61,
        "floor_to": 70,
        "description": (
            "Десять ярусов вампирской саги — испытания, охота, захват и оборона. "
            "Контент: content/data/packs/zones/blood_spire/"
        ),
        "floor_type": "trial_hardcore",
    },
    {
        "key": "chaos_abyss",
        "name": "Бездна Хаоса",
        "emoji": "🌀",
        "floor_from": 71,
        "floor_to": 80,
        "description": "Демоны и искажённые духи ломают разум.",
    },
    {
        "key": "eternity_hall",
        "name": "Зал Вечности",
        "emoji": "⚡",
        "floor_from": 81,
        "floor_to": 99,
        "description": "Архидемоны и стражи вечности. Вершина известной карты — дальше туман.",
    },
)

# Финал башни (135) и этажи 101+ отключены — см. packs/registry.json
ZONE_FINAL_RAW: dict[str, Any] | None = None

# Ключ — after_floor: город между этим ярусом и следующим (не занимает боевой этаж).
CITIES_RAW: dict[int, dict[str, Any]] = {
    0: {
        "key": "quiet_brook",
        "after_floor": 0,
        "name": "Тихий Ручей",
        "emoji": "🏘️",
        "theme_ru": "Деревня между подножием и 1-м ярусом — безопасный очаг",
    },
    30: {
        "key": "ironfall",
        "after_floor": 30,
        "name": "Айронфолл",
        "emoji": "🏙️",
        "theme_ru": "Ледяной форпост между 30 и 31 — викинги и кузни",
    },
    60: {
        "key": "emberhall",
        "after_floor": 60,
        "name": "Эмберхолл",
        "emoji": "🏙️",
        "theme_ru": "Последний огонь между 60 и Кровавым Шпилем",
    },
    90: {
        "key": "eternis",
        "after_floor": 90,
        "name": "Этернис",
        "emoji": "🏙️",
        "theme_ru": "Город между 90 и порогом Зала Вечности",
    },
}
