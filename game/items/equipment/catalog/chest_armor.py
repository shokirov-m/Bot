"""Нагрудная броня — примеры каталога."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png


def armor_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Кольчуга нижнего яруса",
            "kind": "armor",
            "rarity": "common",
            "defense": 2,
            "vit": 1,
            "summary": "Ржавые кольца, но лучше голой груди.",
            "image_url": item_gear_png("catalog_armor_01"),
        },
        {
            "name": "Жилет лазутчика",
            "kind": "armor",
            "rarity": "common",
            "defense": 3,
            "dex": 1,
            "summary": "Лёгкая накладка — не стесняет шага на узких ступенях.",
            "image_url": item_gear_png("catalog_armor_02"),
        },
        {
            "name": "Набрудник послушника",
            "kind": "armor",
            "rarity": "uncommon",
            "defense": 4,
            "vit": 1,
            "str": 1,
            "summary": "Простая сталь, выданная орденом первых колец.",
            "image_url": item_gear_png("catalog_armor_03"),
        },
        {
            "name": "Плащ мшистого камня",
            "kind": "armor",
            "rarity": "common",
            "defense": 2,
            "int": 1,
            "summary": "Пахнет сыростью и чуть держит магический ветер.",
            "image_url": item_gear_png("catalog_armor_04"),
        },
        {
            "name": "Брига из старых знамён",
            "kind": "armor",
            "rarity": "uncommon",
            "defense": 4,
            "luck": 1,
            "summary": "Лоскуты ткани поверх железа — удача тех, кто вернулся.",
            "image_url": item_gear_png("catalog_armor_05"),
        },
        {
            "name": "Кираса стража перил",
            "kind": "armor",
            "rarity": "rare",
            "defense": 6,
            "vit": 2,
            "summary": "Носилась у перил внутреннего кольца; выдерживает удар.",
            "image_url": item_gear_png("catalog_armor_06"),
        },
        {
            "name": "Латы надежды",
            "kind": "armor",
            "rarity": "rare",
            "defense": 7,
            "vit": 2,
            "str": 1,
            "summary": "Тяжёлые, но после них ступени кажутся ровнее.",
            "image_url": item_gear_png("catalog_armor_07"),
        },
        {
            "name": "Кираса золотого кольца",
            "kind": "armor",
            "rarity": "epic",
            "defense": 8,
            "vit": 2,
            "str": 2,
            "summary": "Редкий дар за подъём: золотая окантовка не тускнеет.",
            "image_url": item_gear_png("catalog_armor_08"),
        },
    ]
    return finalize_stub_list(rows)
