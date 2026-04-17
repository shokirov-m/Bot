"""
Категории предметов для сумки и аукциона: экипировка, расходники, прочее.
"""

from __future__ import annotations

from typing import Any

from game.items.equipment import resolve_equip_slot_for_item_data

# Короткие коды для callback_data (2 символа).
BAG_CAT_ALL = "al"
BAG_CAT_EQUIP = "eq"
BAG_CAT_USE = "us"
BAG_CAT_OTHER = "ot"

BAG_CAT_LABEL_RU: dict[str, str] = {
    BAG_CAT_ALL: "Все",
    BAG_CAT_EQUIP: "Экипировка",
    BAG_CAT_USE: "Расходники",
    BAG_CAT_OTHER: "Прочее",
}


def bag_category_label_ru(cat: str) -> str:
    """Подпись категории сумки для UI."""
    return BAG_CAT_LABEL_RU.get(cat, cat)


EQUIP_KINDS: frozenset[str] = frozenset(
    {
        "weapon",
        "armor",
        "helmet",
        "gloves",
        "ring",
        "amulet",
        "pants",
        "boots",
        "cloak",
        "shield",
        "grimoire",
        "tome",
        "orb",
        "focus",
    },
)


def bag_category_for_item_data(item_data: dict[str, Any] | None) -> str:
    """Возвращает BAG_CAT_* для одного предмета."""
    data = item_data or {}
    kind = str(data.get("kind") or "").lower()
    if kind in EQUIP_KINDS or resolve_equip_slot_for_item_data(data) is not None:
        return BAG_CAT_EQUIP
    utag = str(data.get("use_tag") or "").strip()
    if kind == "consumable" or utag:
        return BAG_CAT_USE
    return BAG_CAT_OTHER


def item_data_matches_bag_category(item_data: dict[str, Any] | None, cat: str) -> bool:
    if not cat or cat == BAG_CAT_ALL:
        return True
    return bag_category_for_item_data(item_data) == cat


def item_data_matches_equip_slot(item_data: dict[str, Any] | None, target_slot: str | None) -> bool:
    """True если предмет надевается в указанный слот (для фильтра сумки с экрана экипировки)."""
    if not target_slot:
        return True
    slot = resolve_equip_slot_for_item_data(item_data or {})
    if slot is None:
        return False
    ts = str(target_slot).strip()
    if ts in ("ring", "ring2"):
        return slot in ("ring", "ring2") and str((item_data or {}).get("kind") or "").lower() == "ring"
    return slot == ts
