"""Амулеты — примеры каталога."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png


def amulet_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Кулон сухой пыли",
            "kind": "amulet",
            "rarity": "common",
            "defense": 1,
            "int": 1,
            "summary": "Внутри — крошечный осадок с первого этажа.",
            "image_url": item_gear_png("catalog_amulet_01"),
        },
        {
            "name": "Медальон стойкости",
            "kind": "amulet",
            "rarity": "common",
            "defense": 1,
            "vit": 1,
            "summary": "Тёплый металл у груди успокаивает дыхание.",
            "image_url": item_gear_png("catalog_amulet_02"),
        },
        {
            "name": "Амулет трёх линий",
            "kind": "amulet",
            "rarity": "uncommon",
            "defense": 2,
            "int": 2,
            "summary": "Три насечки — три обещания башни.",
            "image_url": item_gear_png("catalog_amulet_03"),
        },
        {
            "name": "Подвеска удачливого шага",
            "kind": "amulet",
            "rarity": "uncommon",
            "defense": 1,
            "luck": 2,
            "summary": "Кость и серебро — мелкий талисман.",
            "image_url": item_gear_png("catalog_amulet_04"),
        },
        {
            "name": "Ожерелье змеиных чешуй",
            "kind": "amulet",
            "rarity": "uncommon",
            "defense": 2,
            "dex": 1,
            "int": 1,
            "summary": "Чешуя переливается в полумраке лестницы.",
            "image_url": item_gear_png("catalog_amulet_05"),
        },
        {
            "name": "Ключ-сердцевина",
            "kind": "amulet",
            "rarity": "rare",
            "defense": 2,
            "int": 3,
            "vit": 1,
            "summary": "Не открывает двери — открывает канал маны.",
            "image_url": item_gear_png("catalog_amulet_06"),
        },
        {
            "name": "Филактерий старшего яруса",
            "kind": "amulet",
            "rarity": "rare",
            "defense": 3,
            "int": 2,
            "luck": 1,
            "summary": "Свиток в капсуле — защитные слова.",
            "image_url": item_gear_png("catalog_amulet_07"),
        },
        {
            "name": "Сердце башни (копия)",
            "kind": "amulet",
            "rarity": "epic",
            "defense": 3,
            "vit": 2,
            "int": 2,
            "luck": 1,
            "summary": "Подделка легенды; всё же сильный резонанс.",
            "image_url": item_gear_png("catalog_amulet_08"),
        },
    ]
    return finalize_stub_list(rows)
