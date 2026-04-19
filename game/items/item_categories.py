"""
Категории предметов для сумки и аукциона: экипировка, расходники, прочее.
"""

from __future__ import annotations

from typing import Any

from game.items.equipment import resolve_equip_slot_for_item_data

# Секции главного экрана сумки (2 символа; callback inv:sec:<sec>:<page>).
INV_SEC_WEAPON = "wp"
INV_SEC_ARMOR_BODY = "bd"
INV_SEC_ACCESSORY = "ax"
INV_SEC_HELMET = "hm"
INV_SEC_PANTS = "pt"
INV_SEC_CONSUMABLE = "cn"
INV_SEC_RESOURCE = "rs"
INV_SEC_OTHER_GEAR = "og"

ALL_INV_SECTIONS: frozenset[str] = frozenset(
    {
        INV_SEC_WEAPON,
        INV_SEC_ARMOR_BODY,
        INV_SEC_ACCESSORY,
        INV_SEC_HELMET,
        INV_SEC_PANTS,
        INV_SEC_CONSUMABLE,
        INV_SEC_RESOURCE,
        INV_SEC_OTHER_GEAR,
    },
)

INV_SECTION_TITLE_RU: dict[str, str] = {
    INV_SEC_WEAPON: "🗡️ Оружие и вторая рука",
    INV_SEC_ARMOR_BODY: "🦺 Броня",
    INV_SEC_ACCESSORY: "💍 Кольца и амулет",
    INV_SEC_HELMET: "⛑️ Шлем",
    INV_SEC_PANTS: "👖 Поножи",
    INV_SEC_CONSUMABLE: "🧪 Расходники",
    INV_SEC_RESOURCE: "📦 Ресурсы",
    INV_SEC_OTHER_GEAR: "🧤 Перчатки",
}


def inv_section_title_ru(sec: str) -> str:
    return INV_SECTION_TITLE_RU.get(sec, sec)


def equip_slot_to_inv_section(slot: str | None) -> str:
    """Пустой слот экипировки → секция сумки для подбора предметов."""
    s = str(slot or "").strip().lower()
    if s in ("weapon", "offhand"):
        return INV_SEC_WEAPON
    if s == "armor":
        return INV_SEC_ARMOR_BODY
    if s in ("ring", "ring2"):
        return INV_SEC_ACCESSORY
    if s == "helmet":
        return INV_SEC_HELMET
    if s == "pants":
        return INV_SEC_PANTS
    if s == "gloves":
        return INV_SEC_OTHER_GEAR
    return INV_SEC_WEAPON


def item_data_matches_inv_section(item_data: dict[str, Any] | None, sec: str) -> bool:
    """Фильтр предметов сумки по секции главного меню инвентаря."""
    if not sec or sec not in ALL_INV_SECTIONS:
        return False
    data = item_data or {}
    kind = str(data.get("kind") or "").lower()
    if sec == INV_SEC_WEAPON:
        sl = resolve_equip_slot_for_item_data(data)
        return sl in ("weapon", "offhand")
    if sec == INV_SEC_ARMOR_BODY:
        return kind == "armor"
    if sec == INV_SEC_ACCESSORY:
        return kind in ("ring", "amulet")
    if sec == INV_SEC_HELMET:
        return kind == "helmet"
    if sec == INV_SEC_PANTS:
        return kind == "pants"
    if sec == INV_SEC_CONSUMABLE:
        return bag_category_for_item_data(data) == BAG_CAT_USE
    if sec == INV_SEC_RESOURCE:
        return bag_category_for_item_data(data) == BAG_CAT_OTHER
    if sec == INV_SEC_OTHER_GEAR:
        return kind == "gloves"
    return False


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
