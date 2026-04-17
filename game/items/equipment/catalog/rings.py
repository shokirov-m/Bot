"""Кольца — баланс v2.0; картинка — заглушка."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png

_IMG = item_gear_png("placeholder_item")


def ring_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Обручальное Кольцо Башни",
            "kind": "ring",
            "rarity": "common",
            "defense": 8,
            "luck": 8,
            "summary": "Первое кольцо, которое получает восходящий. Символ контракта с Башней.",
            "image_url": _IMG,
        },
        {
            "name": "Кольцо Выносливости",
            "kind": "ring",
            "rarity": "common",
            "defense": 10,
            "vit": 10,
            "ring_slot": 2,
            "summary": "Простое, но тяжелое. Постоянно напоминает о себе на пальце.",
            "image_url": _IMG,
        },
        {
            "name": "Печатка Ловкача",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 25,
            "dex": 20,
            "summary": "Узор на камне движется, когда рядом опасность.",
            "image_url": _IMG,
        },
        {
            "name": "Кольцо Синей Искры",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 22,
            "int": 22,
            "summary": "Покалывает кожу. Ускоряет восстановление маны.",
            "image_url": _IMG,
        },
        {
            "name": "Обруч Стальной Воли",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 30,
            "str": 15,
            "vit": 5,
            "summary": "Хватка становится железной, рука не дрогнет.",
            "image_url": _IMG,
        },
        {
            "name": "Кольцо Двойного Дна",
            "kind": "ring",
            "rarity": "rare",
            "defense": 60,
            "dex": 20,
            "luck": 25,
            "summary": "Внутри кольца спрятано еще одно. Шанс найти дополнительный лут увеличен.",
            "image_url": _IMG,
        },
        {
            "name": "Перстень Алой Крови",
            "kind": "ring",
            "rarity": "rare",
            "defense": 65,
            "str": 25,
            "vit": 25,
            "summary": "Рубин в оправе пульсирует в такт сердцу владельца. Вампиризм 5%.",
            "image_url": _IMG,
        },
        {
            "name": "Кольцо Ста Испытаний",
            "kind": "ring",
            "rarity": "epic",
            "defense": 145,
            "int": 30,
            "luck": 30,
            "vit": 20,
            "summary": "Легенда гласит, что оно было создано из слез Хранителя 100-го этажа.",
            "image_url": _IMG,
        },
        {
            "name": "Вечность",
            "kind": "ring",
            "rarity": "legendary",
            "defense": 250,
            "int": 50,
            "vit": 50,
            "luck": 50,
            "summary": "Золотое кольцо без единого шва. Не дает владельцу умереть, один раз в день восстанавливая 50% здоровья при смертельном ударе.",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)
