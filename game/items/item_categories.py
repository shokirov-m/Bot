"""
Категории предметов для сумки и аукциона: экипировка, расходники, прочее.
"""

from __future__ import annotations

from typing import Any

from game.items.equipment import equip_slot_for_kind

# Короткие коды для callback_data (2 символа).
BAG_CAT_ALL = "al"
BAG_CAT_EQUIP = "eq"
BAG_CAT_USE = "us"
BAG_CAT_OTHER = "ot"

EQUIP_KINDS: frozenset[str] = frozenset({"weapon", "armor", "helmet", "gloves", "ring", "amulet"})


def bag_category_for_item_data(item_data: dict[str, Any] | None) -> str:
    """Возвращает BAG_CAT_* для одного предмета."""
    data = item_data or {}
    kind = str(data.get("kind") or "").lower()
    if kind in EQUIP_KINDS or (kind and equip_slot_for_kind(kind) is not None):
        return BAG_CAT_EQUIP
    utag = str(data.get("use_tag") or "").strip()
    if kind == "consumable" or utag:
        return BAG_CAT_USE
    return BAG_CAT_OTHER


def item_data_matches_bag_category(item_data: dict[str, Any] | None, cat: str) -> bool:
    if not cat or cat == BAG_CAT_ALL:
        return True
    return bag_category_for_item_data(item_data) == cat
