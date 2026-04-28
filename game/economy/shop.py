"""
Торговец: ассортимент расходников за золото + VIP-раздел за Telegram Stars.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from game.floors import floor_data
from utils.image_assets import item_gear_png


@dataclass(frozen=True, slots=True)
class ShopGood:
    key: str
    name: str
    emoji: str
    price: int              # цена в золоте (0 — только за звёзды)
    blurb: str
    item_data: dict[str, Any]
    stars_price: int = 0    # цена в Telegram Stars (0 — не продаётся за звёзды)


# ---------------------------------------------------------------------------
# Обычный магазин — расходники за золото
# ---------------------------------------------------------------------------

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
        key="ration_stale",
        name="Зачерствевший паёк",
        emoji="🍞",
        price=24,
        blurb="Восстанавливает 10% макс. HP в бою.",
        item_data={
            "name": "Зачерствевший паёк",
            "kind": "consumable",
            "rarity": "common",
            "summary": "В бою: +10% к макс. HP.",
            "use_tag": "heal_hp_pct",
            "use_value": 10,
            "image_url": item_gear_png("shop_ration"),
        },
    ),
    ShopGood(
        key="ration_fresh",
        name="Свежий паёк",
        emoji="🥪",
        price=58,
        blurb="Восстанавливает 25% макс. HP в бою.",
        item_data={
            "name": "Свежий паёк",
            "kind": "consumable",
            "rarity": "common",
            "summary": "В бою: +25% к макс. HP.",
            "use_tag": "heal_hp_pct",
            "use_value": 25,
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

# ---------------------------------------------------------------------------
# VIP-магазин — облики за Telegram Stars ⭐
# ---------------------------------------------------------------------------

VIP_STAR_GOODS: tuple[ShopGood, ...] = (
    ShopGood(
        key="prt_noble",
        name="👑 Владыка Башни",
        emoji="👑",
        price=0,
        stars_price=30,
        blurb="Аристократ, покоривший вершины Башни. Редкий облик для профиля.",
        item_data={
            "virtual_shop": "portrait_unlock",
            "portrait_key": "noble_1",
            "name": "👑 Владыка Башни",
        },
    ),
    ShopGood(
        key="prt_arcane",
        name="⭐ Хранитель Архива",
        emoji="⭐",
        price=0,
        stars_price=30,
        blurb="Хранитель запретных знаний архивов. Редкий облик для профиля.",
        item_data={
            "virtual_shop": "portrait_unlock",
            "portrait_key": "arcane_1",
            "name": "⭐ Хранитель Архива",
        },
    ),
)

# Обратная совместимость (аукцион и другие места)
SHOP_PORTRAITS = VIP_STAR_GOODS


def shop_goods_for_floor(floor_number: int) -> tuple[ShopGood, ...]:
    """Расходники у торговца на этаже / в городе."""
    return SHOP_GOODS


def good_by_key(key: str, *, floor_number: int) -> ShopGood | None:
    k = key.strip().lower()
    for g in shop_goods_for_floor(floor_number):
        if g.key == k:
            return g
    for g in VIP_STAR_GOODS:
        if g.key == k:
            return g
    return None


def vip_good_by_key(key: str) -> ShopGood | None:
    k = key.strip().lower()
    for g in VIP_STAR_GOODS:
        if g.key == k:
            return g
    return None


def effective_good_price(base_price: int, floor_number: int) -> int:
    """Цена с наценкой за высоту башни: +1.5% за этаж до 50."""
    f = max(1, min(135, int(floor_number)))
    mult = 1.0 + min(f, 50) * 0.015
    return max(1, math.ceil(base_price * mult - 1e-9))


def shop_available_on_floor(floor_number: int) -> bool:
    if floor_data.get_city_for_floor(floor_number) is not None:
        return True
    return floor_data.has_trader(floor_number)
