"""Перчатки — примеры каталога."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png


def gloves_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Перчатки пыльной лестницы",
            "kind": "gloves",
            "rarity": "common",
            "defense": 1,
            "dex": 1,
            "summary": "Ладони не скользят по перилам.",
            "image_url": item_gear_png("catalog_gloves_01"),
        },
        {
            "name": "Рукавицы кузнеца башни",
            "kind": "gloves",
            "rarity": "common",
            "defense": 2,
            "str": 1,
            "summary": "Толстая кожа и припой на швах.",
            "image_url": item_gear_png("catalog_gloves_02"),
        },
        {
            "name": "Перчатки тонкой работы",
            "kind": "gloves",
            "rarity": "uncommon",
            "defense": 1,
            "dex": 2,
            "luck": 1,
            "summary": "Для тех, кто предпочитает точный удар.",
            "image_url": item_gear_png("catalog_gloves_03"),
        },
        {
            "name": "Накладки чтеца рун",
            "kind": "gloves",
            "rarity": "uncommon",
            "defense": 1,
            "int": 2,
            "summary": "Подсказки символов вышиты на внутренней стороне.",
            "image_url": item_gear_png("catalog_gloves_04"),
        },
        {
            "name": "Когти верёвочника",
            "kind": "gloves",
            "rarity": "common",
            "defense": 1,
            "vit": 1,
            "summary": "Металлические накладки на пальцах.",
            "image_url": item_gear_png("catalog_gloves_05"),
        },
        {
            "name": "Перчатки стального жука",
            "kind": "gloves",
            "rarity": "rare",
            "defense": 3,
            "dex": 1,
            "str": 1,
            "summary": "Сегменты как у панциря.",
            "image_url": item_gear_png("catalog_gloves_06"),
        },
        {
            "name": "Рукавицы белого пламени",
            "kind": "gloves",
            "rarity": "rare",
            "defense": 2,
            "int": 2,
            "vit": 1,
            "summary": "Не обжигают владельца при коротком контакте с огнём.",
            "image_url": item_gear_png("catalog_gloves_07"),
        },
        {
            "name": "Перстни семи печатей",
            "kind": "gloves",
            "rarity": "epic",
            "defense": 3,
            "luck": 2,
            "int": 1,
            "summary": "На каждом пальце — свой знак башни.",
            "image_url": item_gear_png("catalog_gloves_08"),
        },
    ]
    return finalize_stub_list(rows)
