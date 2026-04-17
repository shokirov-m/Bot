"""Поножи — примеры каталога."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png


def pants_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Простые поножи новичка",
            "kind": "pants",
            "rarity": "common",
            "defense": 1,
            "vit": 1,
            "summary": "Грубая кожа на коленях.",
            "image_url": item_gear_png("catalog_pants_01"),
        },
        {
            "name": "Штаны канатного моста",
            "kind": "pants",
            "rarity": "common",
            "defense": 2,
            "dex": 1,
            "summary": "Усилены на сгибах — меньше натирания о верёвку.",
            "image_url": item_gear_png("catalog_pants_02"),
        },
        {
            "name": "Поножи бродячего мага",
            "kind": "pants",
            "rarity": "uncommon",
            "defense": 2,
            "int": 1,
            "vit": 1,
            "summary": "В швах спрятаны слабые защитные руны.",
            "image_url": item_gear_png("catalog_pants_03"),
        },
        {
            "name": "Обмотки скалолаза",
            "kind": "pants",
            "rarity": "common",
            "defense": 1,
            "dex": 2,
            "summary": "Для тех, кто лезет по мокрому камню башни.",
            "image_url": item_gear_png("catalog_pants_04"),
        },
        {
            "name": "Штаны охотника за тайниками",
            "kind": "pants",
            "rarity": "uncommon",
            "defense": 3,
            "luck": 1,
            "summary": "Карманы глубже обычного — мелочь не теряется.",
            "image_url": item_gear_png("catalog_pants_05"),
        },
        {
            "name": "Кольчужные поножи дозора",
            "kind": "pants",
            "rarity": "rare",
            "defense": 4,
            "vit": 2,
            "summary": "Нижняя часть обмундирования стражи этажа.",
            "image_url": item_gear_png("catalog_pants_06"),
        },
        {
            "name": "Поножи кровавого рассвета",
            "kind": "pants",
            "rarity": "rare",
            "defense": 4,
            "str": 1,
            "vit": 1,
            "summary": "Тёмные пятна со временем становятся частью узора.",
            "image_url": item_gear_png("catalog_pants_07"),
        },
        {
            "name": "Набедренник серебряной нити",
            "kind": "pants",
            "rarity": "epic",
            "defense": 5,
            "dex": 2,
            "vit": 1,
            "summary": "Серебро вшито по линиям сгиба — плавный шаг в бою.",
            "image_url": item_gear_png("catalog_pants_08"),
        },
    ]
    return finalize_stub_list(rows)
