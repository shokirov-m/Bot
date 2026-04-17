"""Нагрудная броня — баланс v2.0; картинка — заглушка."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png

_IMG = item_gear_png("placeholder_item")


def armor_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Кольчуга Ополченца",
            "kind": "armor",
            "rarity": "common",
            "defense": 15,
            "vit": 5,
            "summary": "Простые, но надежные кольца. Спасут от удара когтей низшего монстра.",
            "image_url": _IMG,
        },
        {
            "name": "Бригантина Тихого Шага",
            "kind": "armor",
            "rarity": "common",
            "defense": 18,
            "dex": 5,
            "summary": "Пластины вшиты внутрь кожи. Не гремит и не стесняет движений.",
            "image_url": _IMG,
        },
        {
            "name": "Кираса Авангарда",
            "kind": "armor",
            "rarity": "uncommon",
            "defense": 40,
            "str": 8,
            "vit": 8,
            "summary": "Стальной нагрудник, выдержавший не один штурм лестницы.",
            "image_url": _IMG,
        },
        {
            "name": "Ряса Послушника",
            "kind": "armor",
            "rarity": "uncommon",
            "defense": 35,
            "int": 10,
            "vit": 5,
            "summary": "Ткань пропитана защитными эфирными маслами. Немного смягчает магические атаки.",
            "image_url": _IMG,
        },
        {
            "name": "Броня Старых Знамён",
            "kind": "armor",
            "rarity": "uncommon",
            "defense": 45,
            "luck": 10,
            "summary": "Лоскуты знамен поверх металла. Говорят, они приносят удачу тем, кто идет до конца.",
            "image_url": _IMG,
        },
        {
            "name": "Латы Стража Предела",
            "kind": "armor",
            "rarity": "rare",
            "defense": 80,
            "vit": 20,
            "str": 10,
            "summary": "Тяжелая броня для защиты узких коридоров. Вес компенсируется живучестью.",
            "image_url": _IMG,
        },
        {
            "name": "Доспех Падшего Рыцаря",
            "kind": "armor",
            "rarity": "rare",
            "defense": 90,
            "str": 15,
            "vit": 15,
            "summary": "Вороненая сталь с зазубринами от когтей. Внушает уважение и ужас.",
            "image_url": _IMG,
        },
        {
            "name": "Золотой Бастион",
            "kind": "armor",
            "rarity": "epic",
            "defense": 160,
            "str": 25,
            "vit": 30,
            "luck": 10,
            "summary": "Сияющий доспех, в котором отражается свет будущей победы. Значительно снижает весь входящий урон.",
            "image_url": _IMG,
        },
        {
            "name": "Панцирь Первого Хранителя",
            "kind": "armor",
            "rarity": "legendary",
            "defense": 280,
            "vit": 60,
            "str": 40,
            "summary": "Чешуя, сброшенная Древним Драконом у основания Башни. Непробиваем.",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)
