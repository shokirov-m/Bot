"""Поножи — баланс v2.0; картинка — заглушка."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png

_IMG = item_gear_png("placeholder_item")


def pants_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Штаны Новичка",
            "kind": "pants",
            "rarity": "common",
            "defense": 10,
            "vit": 5,
            "summary": "Крепкая ткань и кожаные вставки на коленях.",
            "image_url": _IMG,
        },
        {
            "name": "Набедренники Следопыта",
            "kind": "pants",
            "rarity": "common",
            "defense": 12,
            "dex": 8,
            "summary": "Не стесняют движений при беге по спиральным лестницам.",
            "image_url": _IMG,
        },
        {
            "name": "Поножи Магистра",
            "kind": "pants",
            "rarity": "uncommon",
            "defense": 30,
            "int": 12,
            "vit": 6,
            "summary": "В швах мерцают руны ускорения мысли.",
            "image_url": _IMG,
        },
        {
            "name": "Обмотки Скалолаза",
            "kind": "pants",
            "rarity": "uncommon",
            "defense": 28,
            "dex": 15,
            "luck": 5,
            "summary": "Идеальное сцепление с любой поверхностью. Невозможно поскользнуться.",
            "image_url": _IMG,
        },
        {
            "name": "Поножи Охотника за Головами",
            "kind": "pants",
            "rarity": "uncommon",
            "defense": 35,
            "str": 10,
            "vit": 5,
            "summary": "Множество карманов для метательных ножей и зелий.",
            "image_url": _IMG,
        },
        {
            "name": "Кольчужные Чулки Дозора",
            "kind": "pants",
            "rarity": "rare",
            "defense": 70,
            "vit": 25,
            "summary": "Надежная защита бедер и голени. Выдерживают прямой удар копьем.",
            "image_url": _IMG,
        },
        {
            "name": "Набедренники Кровавой Жатвы",
            "kind": "pants",
            "rarity": "rare",
            "defense": 75,
            "str": 20,
            "vit": 15,
            "summary": "Бурые разводы на стали — напоминание о пройденных битвах. Увеличивает сопротивление кровотечению.",
            "image_url": _IMG,
        },
        {
            "name": "Шаг Сквозь Измерения",
            "kind": "pants",
            "rarity": "epic",
            "defense": 145,
            "dex": 30,
            "vit": 20,
            "summary": "Серебряные нити вплетены в ткань. Позволяют совершать короткий рывок (блок).",
            "image_url": _IMG,
        },
        {
            "name": "Поножи Царя Гор",
            "kind": "pants",
            "rarity": "legendary",
            "defense": 250,
            "str": 35,
            "vit": 45,
            "summary": "Кажется, что они весят целую тонну, но для владельца они легче пуха. Стойкость несгибаема.",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)
