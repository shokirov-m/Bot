"""
Торговец за золото: ассортимент расходников (сумка). Цены базовые, без аукциона.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from game.floors import floor_data
from game.items.equipment.item_asset_paths import item_gear_png


@dataclass(frozen=True, slots=True)
class ShopGood:
    key: str
    name: str
    emoji: str
    price: int
    blurb: str
    item_data: dict[str, Any]


SHOP_GOODS: tuple[ShopGood, ...] = (
    ShopGood(
        key="vita",
        name="Эликсир жизни",
        emoji="🧪",
        price=32,
        blurb="Восстанавливает 35% макс. HP при использовании.",
        item_data={
            "name": "Малый эликсир жизни",
            "kind": "consumable",
            "rarity": "common",
            "summary": "В бою: +35% к макс. HP (кнопка Предмет).",
            "use_tag": "heal_hp_pct",
            "use_value": 35,
            "image_url": item_gear_png("shop_vita"),
        },
    ),
    ShopGood(
        key="ether",
        name="Эфир маны",
        emoji="💠",
        price=36,
        blurb="Восстанавливает 40% макс. MP при использовании.",
        item_data={
            "name": "Капля эфира маны",
            "kind": "consumable",
            "rarity": "common",
            "summary": "В бою: +40% к макс. MP (кнопка Предмет).",
            "use_tag": "heal_mp_pct",
            "use_value": 40,
            "image_url": item_gear_png("shop_ether"),
        },
    ),
    ShopGood(
        key="ration",
        name="Походный паёк",
        emoji="🥖",
        price=48,
        blurb="+2 стамины вне боя (до максимума).",
        item_data={
            "name": "Походный паёк",
            "kind": "consumable",
            "rarity": "common",
            "summary": "Съесть вне боя: +2 ⚡.",
            "use_tag": "stamina_flat",
            "use_value": 2,
            "image_url": item_gear_png("shop_ration"),
        },
    ),
    ShopGood(
        key="antidote",
        name="Противоядие",
        emoji="🧴",
        price=22,
        blurb="Снимает яд в бою (один заряд).",
        item_data={
            "name": "Противоядие",
            "kind": "consumable",
            "rarity": "common",
            "summary": "В бою: снять яд (кнопка Предмет).",
            "use_tag": "cure_poison",
            "use_value": 1,
            "image_url": item_gear_png("shop_antidote"),
        },
    ),
)

# Только этаж 3: простая экипировка за золото (лавка нижнего яруса).
SHOP_FLOOR3_GEAR: tuple[ShopGood, ...] = (
    ShopGood(
        key="f3_ring_str",
        name="Кольцо первого кольца",
        emoji="💍",
        price=55,
        blurb="⚪ Обычное · +1 удача, +1 защита.",
        item_data={
            "name": "Кольцо первого кольца",
            "kind": "ring",
            "rarity": "common",
            "defense": 1,
            "luck": 1,
            "summary": "Простая оправа — чуть увереннее шаг по ступеням башни.",
            "image_url": item_gear_png("shop_f3_ring"),
        },
    ),
    ShopGood(
        key="f3_gloves_dex",
        name="Перчатки каната",
        emoji="🧤",
        price=48,
        blurb="⚪ Обычное · +1 ловкость.",
        item_data={
            "name": "Перчатки каната",
            "kind": "gloves",
            "rarity": "common",
            "defense": 1,
            "dex": 1,
            "summary": "Обмотки для рук — меньше скольжения на мокром камне.",
            "image_url": item_gear_png("shop_f3_gloves"),
        },
    ),
    ShopGood(
        key="f3_amulet_vit",
        name="Обсидиановый жетон",
        emoji="📿",
        price=62,
        blurb="⚪ Обычное · +1 выносливость.",
        item_data={
            "name": "Обсидиановый жетон",
            "kind": "amulet",
            "rarity": "common",
            "defense": 1,
            "vit": 1,
            "summary": "Холодный камень у сердца — дышать ровнее в бою.",
            "image_url": item_gear_png("shop_f3_amulet"),
        },
    ),
)


def shop_goods_for_floor(floor_number: int) -> tuple[ShopGood, ...]:
    """Расходники везде; снаряжение — только на 3 этаже."""
    if int(floor_number) == 3:
        return SHOP_GOODS + SHOP_FLOOR3_GEAR
    return SHOP_GOODS


def good_by_key(key: str, *, floor_number: int) -> ShopGood | None:
    k = key.strip().lower()
    for g in shop_goods_for_floor(floor_number):
        if g.key == k:
            return g
    return None


def effective_good_price(base_price: int, floor_number: int) -> int:
    """
    Цена с наценкой за высоту башни: +1.5% за этаж до 50, дальше плато.
    """
    f = max(1, min(100, int(floor_number)))
    mult = 1.0 + min(f, 50) * 0.015
    return max(1, math.ceil(base_price * mult - 1e-9))


def shop_available_on_floor(floor_number: int) -> bool:
    """Лавка на городских этажах и на каждом 5-м (флаг торговца)."""
    if floor_data.get_city_for_floor(floor_number) is not None:
        return True
    return floor_data.has_trader(floor_number)
