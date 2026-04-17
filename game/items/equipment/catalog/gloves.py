"""Перчатки — баланс v2.0; картинка — заглушка."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png

_IMG = item_gear_png("placeholder_item")


def gloves_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Перчатки Работяги",
            "kind": "gloves",
            "rarity": "common",
            "defense": 8,
            "str": 5,
            "summary": "Грубая кожа. Крепко держат рукоять меча или кирку.",
            "image_url": _IMG,
        },
        {
            "name": "Рукавицы Стрелка",
            "kind": "gloves",
            "rarity": "common",
            "defense": 6,
            "dex": 8,
            "summary": "Обрезаны на пальцах для лучшего контакта с тетивой.",
            "image_url": _IMG,
        },
        {
            "name": "Перчатки Ювелира",
            "kind": "gloves",
            "rarity": "uncommon",
            "defense": 20,
            "dex": 15,
            "luck": 10,
            "summary": "Тонкая выделка позволяет чувствовать малейшие вибрации ловушек.",
            "image_url": _IMG,
        },
        {
            "name": "Накладки Чтеца Рун",
            "kind": "gloves",
            "rarity": "uncommon",
            "defense": 18,
            "int": 20,
            "summary": "Руны на тыльной стороне ладони загораются при произнесении заклинания.",
            "image_url": _IMG,
        },
        {
            "name": "Когти Хищника",
            "kind": "gloves",
            "rarity": "uncommon",
            "defense": 25,
            "str": 12,
            "vit": 8,
            "summary": "Металлические накладки на пальцах. Увеличивают урон от рукопашного боя без оружия.",
            "image_url": _IMG,
        },
        {
            "name": "Перчатки Стального Жука",
            "kind": "gloves",
            "rarity": "rare",
            "defense": 55,
            "str": 20,
            "dex": 15,
            "summary": "Сегментированная броня, не сковывающая движений кисти.",
            "image_url": _IMG,
        },
        {
            "name": "Рукавицы Белого Пламени",
            "kind": "gloves",
            "rarity": "rare",
            "defense": 60,
            "int": 25,
            "vit": 15,
            "summary": "Не боятся огня. Увеличивают мощь огненных заклинаний на 10%.",
            "image_url": _IMG,
        },
        {
            "name": "Печать Семи Стихий",
            "kind": "gloves",
            "rarity": "epic",
            "defense": 140,
            "int": 30,
            "luck": 20,
            "dex": 10,
            "summary": "Каждый палец украшен кольцом с символом элемента. Сокращает время каста заклинаний.",
            "image_url": _IMG,
        },
        {
            "name": "Длани Творца",
            "kind": "gloves",
            "rarity": "legendary",
            "defense": 240,
            "str": 45,
            "int": 30,
            "summary": "Эти перчатки касались ткани мироздания. Позволяют использовать навык «Захват Заклинания».",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)
