"""
Усиление экипировки по rarity при чтении из item_data (атака, защита, бонусы статов).
"""

from __future__ import annotations

from typing import Any

_VALID_RARITY = frozenset({"common", "uncommon", "rare", "epic", "legendary"})

_WEAPON_ATK_FLAT: dict[str, int] = {
    "common": 0,
    "uncommon": 1,
    "rare": 2,
    "epic": 4,
    "legendary": 7,
}

_WEAPON_ATK_MULT: dict[str, float] = {
    "common": 1.0,
    "uncommon": 1.05,
    "rare": 1.1,
    "epic": 1.16,
    "legendary": 1.24,
}

_ARMOR_DEF_FLAT: dict[str, int] = {
    "common": 0,
    "uncommon": 1,
    "rare": 2,
    "epic": 4,
    "legendary": 6,
}

_ARMOR_DEF_MULT: dict[str, float] = {
    "common": 1.0,
    "uncommon": 1.04,
    "rare": 1.08,
    "epic": 1.12,
    "legendary": 1.18,
}


def _norm_rarity(item_data: dict[str, Any] | None) -> str:
    if not item_data:
        return "common"
    r = str(item_data.get("rarity") or "common").lower().strip()
    return r if r in _VALID_RARITY else "common"


def scaled_weapon_attack_value(base_attack: int, item_data: dict[str, Any] | None) -> int:
    """Базовая атака с карточки × множитель редкости + небольшой плоский бонус."""
    if base_attack <= 0:
        return base_attack
    r = _norm_rarity(item_data)
    mul = float(_WEAPON_ATK_MULT.get(r, 1.0))
    flat = int(_WEAPON_ATK_FLAT.get(r, 0))
    return max(1, int(round(base_attack * mul)) + flat)


def scaled_armor_defense_value(base_defense: int, item_data: dict[str, Any] | None) -> int:
    """Защита с карточки × множитель редкости + плоский бонус."""
    if base_defense <= 0:
        return 0
    r = _norm_rarity(item_data)
    mul = float(_ARMOR_DEF_MULT.get(r, 1.0))
    flat = int(_ARMOR_DEF_FLAT.get(r, 0))
    return max(0, int(round(base_defense * mul)) + flat)


def extra_stat_points_for_rarity_on_item(item_data: dict[str, Any] | None) -> int:
    """Сколько очков добавить к каждому ненулевому стату (см. stat_bonuses_from_item_data)."""
    return int(
        {
            "common": 0,
            "uncommon": 1,
            "rare": 2,
            "epic": 3,
            "legendary": 4,
        }.get(_norm_rarity(item_data), 0),
    )
