"""Крафт в кузнице: рецепты (материалы → предмет)."""

from __future__ import annotations

import copy
from typing import Any, TypedDict


class CraftRecipeDef(TypedDict, total=False):
    id: str
    name_ru: str
    description: str
    # сколько единиц материала редкости
    cost: dict[str, int]
    result: dict[str, Any]


# Редкости: common, uncommon, rare, epic, legendary, mythic — как в materials.
RECIPES: list[CraftRecipeDef] = [
    {
        "id": "salve_basic",
        "name_ru": "Настой (HP)",
        "description": "2 осколка + 1 сплав: простой флакон.",
        "cost": {"common": 2, "uncommon": 1},
        "result": {
            "name": "🧪 Крафт: настой (HP)",
            "kind": "misc",
            "rarity": "common",
            "use_tag": "heal_hp_flat",
            "use_value": 55,
            "summary": "Сварено в кузне. Восстанавливает HP в бою/после боя.",
        },
    },
    {
        "id": "ring_siphon",
        "name_ru": "Перстень с поглощением",
        "description": "5 common + 2 uncommon: кольцо с слабым lifesteal (пассив экипа).",
        "cost": {"common": 5, "uncommon": 2},
        "result": {
            "name": "🩸 Перстень поглощения",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 0,
            "summary": "Крафт. Пассив: поглощение части наносимого урона.",
            "passive": {"lifesteal_percent": 2.0},
        },
    },
]


def get_recipe_by_id(rid: str) -> CraftRecipeDef | None:
    for r in RECIPES:
        if str(r.get("id")) == rid:
            return r
    return None
