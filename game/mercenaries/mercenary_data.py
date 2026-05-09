"""Генерация процедурных наёмников и цен (база × BLACK_MARKET_PRICE_MULT).

Ограничение пула наёмниц: в игре оставлены только 3 женских архетипа:
- эльфийка с изумрудными волосами
- вампирша
- волкодевушка
"""

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

_MALE_NAMES = (
    "Гром",
    "Кейн",
    "Джек",
    "Орик",
    "Ворн",
    "Крог",
    "Рувар",
)

# Единственные женские наёмники (описания/картинки — через extra).
_FEMALE_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "display_name": "Эльфика (изумрудные волосы)",
        "race_key": "elf",
        "merc_key": "elf_emerald",
        "portrait": "elf_emerald.png",
    },
    {
        "display_name": "Вампирша",
        "race_key": "vampire",
        "merc_key": "vampiress",
        "portrait": "vampiress.png",
    },
    {
        "display_name": "Волкодевушка",
        "race_key": "wolf",
        "merc_key": "wolfgirl",
        "portrait": "wolfgirl.png",
    },
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
    hp = rd.base_hp + level * 8
    atk = rd.base_atk + level * 2

    # Женские лоты — только из 3 заданных.
    # Доля женских на витрине: умеренная, чтобы не «забить» мужиков.
    is_female = rng.random() < 0.35
    if is_female:
        base = dict(rng.choice(_FEMALE_TEMPLATES))
        name = str(base["display_name"])
        race_key = str(base.get("race_key") or "human")
        merc_key = str(base.get("merc_key") or "female")
        portrait = str(base.get("portrait") or "")
        extra = {
            "gender": "female",
            "merc_key": merc_key,
            "portrait": portrait,
        }
    else:
        name = rng.choice(_MALE_NAMES)
        race_key = "human"
        extra = {"gender": "male"}

    return {
        "display_name": name,
        "race_key": race_key,
        "class_role": role_key,
        "rarity": rar,
        "level": level,
        "loyalty": 35 + rng.randint(0, 15),
        "hp_max": hp,
        "atk": atk,
        "price_gold": scaled_price(rar),
        "extra": extra,
    }
