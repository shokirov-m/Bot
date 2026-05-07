"""Генерация процедурных наёмников и цен (база × BLACK_MARKET_PRICE_MULT)."""

from __future__ import annotations

import random
from typing import Any

from game.mercenaries.constants import BLACK_MARKET_PRICE_MULT
from game.mercenaries.mercenary_classes import ROLES, role_def

RARITIES = ("common", "uncommon", "rare", "epic", "legendary")
RARITY_LABEL_RU = {
    "common": "обычный",
    "uncommon": "необычный",
    "rare": "редкий",
    "epic": "эпический",
    "legendary": "легендарный",
}

# Базовая цена до множителя ×10
_BASE_PRICE: dict[str, int] = {
    "common": 800,
    "uncommon": 2200,
    "rare": 6000,
    "epic": 14000,
    "legendary": 32000,
}

_NAMES_A = (
    "Гром", "Лира", "Кейн", "Мира", "Джек", "Сильва", "Орик", "Найра",
    "Ворн", "Эйва", "Крог", "Тесс", "Рувар", "Инга",
)


def scaled_price(rarity: str) -> int:
    base = int(_BASE_PRICE.get(rarity, _BASE_PRICE["common"]))
    return base * BLACK_MARKET_PRICE_MULT


def random_mercenary_payload(*, seed: int | None = None, rarity: str | None = None) -> dict[str, Any]:
    rng = random.Random(seed)
    rar = rarity or rng.choice(RARITIES)
    role_key = rng.choice(tuple(ROLES.keys()))
    rd = role_def(role_key)
    level = 1 + RARITIES.index(rar) * 3 + rng.randint(0, 2)
    name = rng.choice(_NAMES_A)
    hp = rd.base_hp + level * 8
    atk = rd.base_atk + level * 2
    return {
        "display_name": name,
        "race_key": "human",
        "class_role": role_key,
        "rarity": rar,
        "level": level,
        "loyalty": 35 + rng.randint(0, 15),
        "hp_max": hp,
        "atk": atk,
        "price_gold": scaled_price(rar),
    }
