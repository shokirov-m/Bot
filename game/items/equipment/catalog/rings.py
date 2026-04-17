"""Кольца — примеры каталога (слоты ring / ring2; явный палец через ring_slot)."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png


def ring_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Перстень нижнего кольца",
            "kind": "ring",
            "rarity": "common",
            "defense": 1,
            "luck": 1,
            "summary": "Грубая оправа, мелкий резонанс удачи.",
            "image_url": item_gear_png("catalog_ring_01"),
        },
        {
            "name": "Кольцо второго пальца",
            "kind": "ring",
            "rarity": "common",
            "defense": 1,
            "vit": 1,
            "ring_slot": "2",
            "summary": "Сразу надевается во второй слот кольца.",
            "image_url": item_gear_png("catalog_ring_02"),
        },
        {
            "name": "Печатка ловца знаков",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 1,
            "dex": 2,
            "summary": "Узор на камне движется при опасности.",
            "image_url": item_gear_png("catalog_ring_03"),
        },
        {
            "name": "Кольцо синей искры",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 1,
            "int": 2,
            "summary": "Слабый отклик на трату маны.",
            "image_url": item_gear_png("catalog_ring_04"),
        },
        {
            "name": "Обруч стальной воли",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 2,
            "str": 1,
            "summary": "Тяжёлый металл — рука не дрожит при ударе.",
            "image_url": item_gear_png("catalog_ring_05"),
        },
        {
            "name": "Кольцо двойной тени",
            "kind": "ring",
            "rarity": "rare",
            "defense": 2,
            "luck": 2,
            "dex": 1,
            "summary": "Подходит убийце тишины и удачливому вору.",
            "image_url": item_gear_png("catalog_ring_06"),
        },
        {
            "name": "Перстень крови яруса",
            "kind": "ring",
            "rarity": "rare",
            "defense": 2,
            "str": 2,
            "vit": 1,
            "summary": "Камень тёмно-красный, как закат за окном башни.",
            "image_url": item_gear_png("catalog_ring_07"),
        },
        {
            "name": "Кольцо ста испытаний",
            "kind": "ring",
            "rarity": "epic",
            "defense": 3,
            "luck": 2,
            "int": 2,
            "summary": "Легендарный символ пути наверх.",
            "image_url": item_gear_png("catalog_ring_08"),
        },
    ]
    return finalize_stub_list(rows)
