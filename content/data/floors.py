"""
Зоны, финал, города-хабы — сырые dict для game/tower/progression/floor_data.py.
Эпитеты и функции этажей остаются в floor_data.
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
        "key": "sky_citadel",
        "name": "Небесная Крепость",
        "emoji": "☁️",
        "floor_from": 61,
        "floor_to": 70,
        "description": "Вихри, грифоны и падшие ангелы хаоса.",
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
        "description": "Архидемоны и стражи вечности.",
    },
)


# Тип этажа: "normal" | "survival" | "faction_war"
# survival: глобальный дебафф — нужен защитный предмет
# faction_war: война фракций — 1000 репутации для вызова босса

ZONES_RAW = ZONES_RAW + (
    {
        "key": "jade_labyrinth",
        "name": "Нефритовый Лабиринт",
        "emoji": "💚",
        "floor_from": 101,
        "floor_to": 110,
        "description": "Запутанные залы нефритового храма. Слепые стражи и ловушки древних мудрецов.",
        "floor_type": "normal",
    },
    {
        "key": "frozen_wastes",
        "name": "Морозные Пустоши",
        "emoji": "🥶",
        "floor_from": 111,
        "floor_to": 120,
        "description": (
            "Выживание: смертельный холод отнимает HP каждую минуту. "
            "Для защиты нужен Амулет Тепла (алхимик в Городе Новичков)."
        ),
        "floor_type": "survival",
        "debuff": {
            "kind": "hp_decay",
            "hp_per_min": 50,
            "protection_item": "warmth_amulet",
            "protection_item_name": "Амулет Тепла",
            "damage_reduction": 0.0,
        },
    },
    {
        "key": "faction_war_plains",
        "name": "Поля Вечной Войны",
        "emoji": "⚔️",
        "floor_from": 121,
        "floor_to": 134,
        "description": "Война Фракций: Эльфы Света vs Орки Крови. Выбери сторону и набери 1000 репутации чтобы вызвать генерала.",
        "floor_type": "faction_war",
        "factions": {
            "light_elves": {
                "name": "Эльфы Света",
                "emoji": "🧝",
                "enemy_key": "blood_orcs",
                "reward_passive": "elven_grace",
                "reward_passive_name": "Эльфийская Грация",
                "reward_passive_desc": "+15% уклонение, +10% к скорости атаки",
            },
            "blood_orcs": {
                "name": "Орки Крови",
                "emoji": "👹",
                "enemy_key": "light_elves",
                "reward_passive": "orc_fury",
                "reward_passive_name": "Ярость Орков",
                "reward_passive_desc": "+20% физ. урон, +15% к максимальному HP",
            },
        },
        "reputation_required": 1000,
    },
)

ZONE_FINAL_RAW: dict[str, Any] = {
    "key": "tower_warden",
    "name": "Страж Башни",
    "emoji": "👁️",
    "floor_from": 135,
    "floor_to": 135,
    "description": "Финальный страж. Три фазы, легендарный лут.",
    "floor_type": "normal",
}

CITIES_RAW: dict[int, dict[str, Any]] = {
    1: {
        "floor": 1,
        "name": "Тихий Ручей",
        "emoji": "🏘️",
        "theme_ru": "Деревня новичков у подножия башни — тёплый очаг и простые советы",
    },
    31: {
        "floor": 31,
        "name": "Айронфолл",
        "emoji": "🏙️",
        "theme_ru": "Ледяное средневековье, викинги",
    },
    61: {
        "floor": 61,
        "name": "Эмберхолл",
        "emoji": "🏙️",
        "theme_ru": "Вулканический промышленный город гномов",
    },
    91: {
        "floor": 91,
        "name": "Этернис",
        "emoji": "🏙️",
        "theme_ru": "Небесный эндгейм-хаб",
    },
}
