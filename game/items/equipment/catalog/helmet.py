"""Шлемы — примеры каталога."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png


def helmet_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Капюшон странника",
            "kind": "helmet",
            "rarity": "common",
            "defense": 1,
            "dex": 1,
            "summary": "Прячет лицо от сквозняков лестницы.",
            "image_url": item_gear_png("catalog_helmet_01"),
        },
        {
            "name": "Шлем кольца железа",
            "kind": "helmet",
            "rarity": "common",
            "defense": 2,
            "str": 1,
            "summary": "Простой полуоткрытый шлем новобранца.",
            "image_url": item_gear_png("catalog_helmet_02"),
        },
        {
            "name": "Диадема сухого эфира",
            "kind": "helmet",
            "rarity": "uncommon",
            "defense": 2,
            "int": 2,
            "summary": "Узкий обруч — фокус для чтения заклинаний.",
            "image_url": item_gear_png("catalog_helmet_03"),
        },
        {
            "name": "Шапка ночного дозора",
            "kind": "helmet",
            "rarity": "common",
            "defense": 1,
            "vit": 1,
            "summary": "Тёплая подкладка и жёсткий козырёк.",
            "image_url": item_gear_png("catalog_helmet_04"),
        },
        {
            "name": "Маска тихого шага",
            "kind": "helmet",
            "rarity": "uncommon",
            "defense": 2,
            "dex": 2,
            "summary": "Лёгкая кожа с прорезями для глаз.",
            "image_url": item_gear_png("catalog_helmet_05"),
        },
        {
            "name": "Шлем бури",
            "kind": "helmet",
            "rarity": "rare",
            "defense": 3,
            "str": 2,
            "summary": "Усиленный на лоб наконечник — для таранов.",
            "image_url": item_gear_png("catalog_helmet_06"),
        },
        {
            "name": "Корона осколков",
            "kind": "helmet",
            "rarity": "rare",
            "defense": 3,
            "int": 1,
            "luck": 1,
            "summary": "Кристаллы впаяны в обод — ловят блики маны.",
            "image_url": item_gear_png("catalog_helmet_07"),
        },
        {
            "name": "Шлем грома ярусов",
            "kind": "helmet",
            "rarity": "epic",
            "defense": 4,
            "vit": 2,
            "str": 1,
            "summary": "Слышен слабый гул, когда враг близко.",
            "image_url": item_gear_png("catalog_helmet_08"),
        },
    ]
    return finalize_stub_list(rows)
