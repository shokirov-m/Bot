"""Амулеты — баланс v2.0; картинка — заглушка."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png

_IMG = item_gear_png("placeholder_item")


def amulet_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Кулон Пыльного Эха",
            "kind": "amulet",
            "rarity": "common",
            "defense": 8,
            "int": 8,
            "summary": "Внутри маленькой колбы — пыль первого этажа. Слабый источник магии.",
            "image_url": _IMG,
        },
        {
            "name": "Медальон Стойкости",
            "kind": "amulet",
            "rarity": "common",
            "defense": 10,
            "vit": 10,
            "summary": "Теплый металл успокаивает сердцебиение при виде монстра.",
            "image_url": _IMG,
        },
        {
            "name": "Амулет Трех Лун",
            "kind": "amulet",
            "rarity": "uncommon",
            "defense": 30,
            "int": 25,
            "summary": "Три лунных камня, символизирующих фазы подъема.",
            "image_url": _IMG,
        },
        {
            "name": "Подвеска Везунчика",
            "kind": "amulet",
            "rarity": "uncommon",
            "defense": 28,
            "luck": 30,
            "summary": "Потертая монетка на шнурке. Иногда она падает нужной стороной.",
            "image_url": _IMG,
        },
        {
            "name": "Ожерелье из Чешуи",
            "kind": "amulet",
            "rarity": "uncommon",
            "defense": 35,
            "dex": 15,
            "int": 10,
            "summary": "Переливается всеми цветами радуги. Увеличивает сопротивление ядам.",
            "image_url": _IMG,
        },
        {
            "name": "Ключ-Сердцевина",
            "kind": "amulet",
            "rarity": "rare",
            "defense": 70,
            "int": 35,
            "vit": 20,
            "summary": "Не открывает двери, но открывает скрытые резервы организма.",
            "image_url": _IMG,
        },
        {
            "name": "Филактерий Старшего Мага",
            "kind": "amulet",
            "rarity": "rare",
            "defense": 75,
            "int": 40,
            "luck": 15,
            "summary": "Содержит свиток с заклинанием абсолютной защиты. Один раз в бою блокирует летальный урон (перезарядка 5 минут).",
            "image_url": _IMG,
        },
        {
            "name": "Сердце Башни (Осколок)",
            "kind": "amulet",
            "rarity": "epic",
            "defense": 150,
            "int": 45,
            "vit": 35,
            "luck": 25,
            "summary": "Крошечная часть ядра Башни. Значительно усиливает все параметры владельца.",
            "image_url": _IMG,
        },
        {
            "name": "Глаз Бездны",
            "kind": "amulet",
            "rarity": "legendary",
            "defense": 270,
            "int": 70,
            "vit": 60,
            "summary": "Огромный черный алмаз, в глубине которого видна спираль уходящих душ. Позволяет воскрешать поверженных врагов как союзников (раз в день).",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)
