"""Шлемы — баланс v2.0; картинка — заглушка."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png

_IMG = item_gear_png("placeholder_item")


def helmet_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Капюшон Пилигрима",
            "kind": "helmet",
            "rarity": "common",
            "defense": 10,
            "dex": 5,
            "summary": "Прячет лицо от ветра и чужих взглядов.",
            "image_url": _IMG,
        },
        {
            "name": "Шлем Ополчения",
            "kind": "helmet",
            "rarity": "common",
            "defense": 14,
            "str": 5,
            "summary": "Простой железный горшок. Но голову бережет.",
            "image_url": _IMG,
        },
        {
            "name": "Диадема Концентрации",
            "kind": "helmet",
            "rarity": "uncommon",
            "defense": 25,
            "int": 18,
            "summary": "Узкий серебряный обруч. Помогает не сбиться с заклинания в пылу боя.",
            "image_url": _IMG,
        },
        {
            "name": "Шлем Ночного Дозора",
            "kind": "helmet",
            "rarity": "uncommon",
            "defense": 30,
            "vit": 12,
            "dex": 5,
            "summary": "Крепкая сталь с мягким подшлемником. Позволяет видеть в темноте.",
            "image_url": _IMG,
        },
        {
            "name": "Маска Тишины",
            "kind": "helmet",
            "rarity": "uncommon",
            "defense": 28,
            "dex": 20,
            "summary": "Закрывает лицо полностью, оставляя лишь прорезь для глаз. Шанс нанести критический удар.",
            "image_url": _IMG,
        },
        {
            "name": "Шлем Урагана",
            "kind": "helmet",
            "rarity": "rare",
            "defense": 65,
            "str": 25,
            "vit": 10,
            "summary": "Тяжелый, с гребнем. Идеален для таранных ударов головой.",
            "image_url": _IMG,
        },
        {
            "name": "Корона Падших Звезд",
            "kind": "helmet",
            "rarity": "rare",
            "defense": 60,
            "int": 20,
            "luck": 15,
            "summary": "Мелкие кристаллы-осколки мерцают в полумраке, подпитывая владельца маной.",
            "image_url": _IMG,
        },
        {
            "name": "Шлем Небесного Грома",
            "kind": "helmet",
            "rarity": "epic",
            "defense": 150,
            "str": 30,
            "vit": 25,
            "int": 15,
            "summary": "Гудит от напряжения. При получении урона выпускает электрический разряд в обидчика.",
            "image_url": _IMG,
        },
        {
            "name": "Личина Безликого Бога",
            "kind": "helmet",
            "rarity": "legendary",
            "defense": 260,
            "luck": 40,
            "int": 35,
            "summary": "Смотря на эту маску, враги забывают, зачем они сюда пришли. Шанс наложить «Смятение» при ударе.",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)
