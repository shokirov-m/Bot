"""
Материалы для заточки — получаются при разборе экипировки в кузнице.

Каждая редкость даёт свой тип материала; хранятся в сумке как стакуемый предмет
(``kind="material"``, ``count=N``).
"""

from __future__ import annotations

import random
from typing import Any

_MATERIAL_NAMES: dict[str, str] = {
    "common":    "Осколок стали",
    "uncommon":  "Сплав доспеха",
    "rare":      "Кристалл ауры",
    "epic":      "Эпический слиток",
    "legendary": "Легендарная эссенция",
    "mythic":    "Мифический фрагмент",
}

_MATERIAL_EMOJIS: dict[str, str] = {
    "common":    "🪨",
    "uncommon":  "🔩",
    "rare":      "💠",
    "epic":      "🔮",
    "legendary": "⭐",
    "mythic":    "🌟",
}

# Диапазон [lo, hi] материалов при разборе по редкости предмета.
_DISASSEMBLE_RANGES: dict[str, tuple[int, int]] = {
    "common":    (1, 3),
    "uncommon":  (1, 4),
    "rare":      (2, 5),
    "epic":      (2, 5),
    "legendary": (3, 5),
    "mythic":    (3, 5),
}


def material_emoji(rarity: str) -> str:
    return _MATERIAL_EMOJIS.get(str(rarity or "common").lower().strip(), "🪨")


def material_name(rarity: str) -> str:
    r = str(rarity or "common").lower().strip()
    return f"{_MATERIAL_EMOJIS.get(r, '🪨')} {_MATERIAL_NAMES.get(r, 'Материал')}"


def material_payload(rarity: str, count: int = 1) -> dict[str, Any]:
    """item_data для стака материала заточки."""
    r = str(rarity or "common").lower().strip()
    return {
        "name":    material_name(r),
        "kind":    "material",
        "rarity":  r,
        "count":   max(1, int(count)),
        "summary": f"Материал для заточки ({r}). Используется в кузнице.",
    }


def disassemble_material_count(rarity: str) -> int:
    """Сколько материалов даётся при разборе предмета данной редкости."""
    r = str(rarity or "common").lower().strip()
    lo, hi = _DISASSEMBLE_RANGES.get(r, (1, 3))
    return random.randint(lo, hi)


def total_materials_in_bag(bag_items: list[Any], rarity: str) -> int:
    """Суммарный count материалов нужной редкости в сумке."""
    r = str(rarity or "common").lower().strip()
    total = 0
    for it in bag_items:
        d = it.item_data or {}
        if str(d.get("kind")) == "material" and str(d.get("rarity")) == r:
            total += max(1, int(d.get("count", 1)))
    return total


# ---------------------------------------------------------------------------
# Боссовый трофей — особая валюта для улучшения дома (ур. 3-5).
# ---------------------------------------------------------------------------

def boss_trophy_payload(count: int = 1) -> dict[str, Any]:
    """item_data для стака трофеев босса."""
    return {
        "name": "🏆 Трофей босса",
        "kind": "boss_trophy",
        "rarity": "epic",
        "count": max(1, int(count)),
        "summary": "Редкий трофей с могучего босса. Нужен для улучшения дома (ур. 3–5).",
    }


def total_boss_trophies_in_bag(bag_items: list[Any]) -> int:
    """Суммарный count трофеев босса в сумке."""
    total = 0
    for it in bag_items:
        d = it.item_data or {}
        if str(d.get("kind")) == "boss_trophy":
            total += max(1, int(d.get("count", 1)))
    return total
