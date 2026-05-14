"""
Слоты экипировки: основная рука, вторая рука (offhand), поножи и пр.
kind + флаги в item_data → equip_slot в БД.
"""

from __future__ import annotations

from typing import Any

# Порядок в UI: оружие, вторая рука, тело, поножи, голова, руки, два кольца, амулет.
EQUIP_ORDER: tuple[str, ...] = (
    "weapon",
    "offhand",
    "armor",
    "pants",
    "helmet",
    "gloves",
    "ring",
    "ring2",
    "amulet",
)

SLOT_LABEL_RU: dict[str, str] = {
    "weapon": "🗡️ Основная рука",
    "offhand": "🛡️ Вторая рука",
    "armor": "🛡️ Броня",
    "pants": "👖 Поножи",
    "helmet": "⛑️ Шлем",
    "gloves": "🧤 Перчатки",
    "ring": "💍 Кольцо I",
    "ring2": "💍 Кольцо II",
    "amulet": "📿 Амулет",
}

# Тип предмета (kind) → слот по умолчанию (без учёта weapon hand / two_handed).
_KIND_TO_SLOT: dict[str, str] = {
    "weapon": "weapon",
    "armor": "armor",
    "pants": "pants",
    "helmet": "helmet",
    "gloves": "gloves",
    "ring": "ring",  # фактический слот ring / ring2 выбирается при надевании
    "amulet": "amulet",
    "shield": "offhand",
    "grimoire": "offhand",
    "tome": "offhand",
    "orb": "offhand",
    "focus": "offhand",
    "dagger": "offhand",
}


def ring_slot_is_explicit(data: dict[str, Any] | None) -> bool:
    """У кольца указан конкретный палец (ring vs ring2) в item_data."""
    if not data or str(data.get("kind") or "").lower() != "ring":
        return False
    rs = str(data.get("ring_slot", "")).lower().strip()
    return rs in ("1", "left", "ring1", "первое", "2", "right", "ring2", "второе")


def item_is_two_handed(data: dict[str, Any] | None) -> bool:
    if not data:
        return False
    if bool(data.get("two_handed")):
        return True
    g = str(data.get("grip") or "").lower()
    return g in ("2h", "two", "two_handed", "two-handed")


def resolve_equip_slot_for_item_data(data: dict[str, Any] | None) -> str | None:
    """
    Слот экипировки для предмета.
    - weapon + hand=off → offhand (второй кинжал и т.п.)
    - shield / grimoire / tome → offhand
    - weapon по умолчанию → weapon (основная рука)
    - ring + ring_slot → ring или ring2; без ring_slot при надевании слот выбирает inventory_repo
    """
    if not data:
        return None
    kind = str(data.get("kind") or "").lower()
    if kind in ("boots", "cloak"):
        return None
    if not kind:
        return None
    if kind == "weapon":
        hand = str(data.get("hand") or "main").lower()
        if hand in ("off", "offhand", "left", "second"):
            return "offhand"
        return "weapon"
    if kind == "ring":
        rs = str(data.get("ring_slot", "")).lower().strip()
        if rs in ("2", "right", "ring2", "второе"):
            return "ring2"
        if rs in ("1", "left", "ring1", "первое"):
            return "ring"
        return "ring"  # без явного пальца — инвентарь подставит ring или ring2
    return _KIND_TO_SLOT.get(kind)


def equip_slot_for_kind(kind: str | None) -> str | None:
    """Упрощённо: только по kind (без hand). Для weapon всегда основная рука."""
    if not kind:
        return None
    k = str(kind).lower()
    if k in ("boots", "cloak"):
        return None
    if k == "weapon":
        return "weapon"
    return _KIND_TO_SLOT.get(k)


def slot_label_ru(slot: str) -> str:
    return SLOT_LABEL_RU.get(slot, slot)


# Подпись kind в карточках и фильтрах (русский UI).
ITEM_KIND_LABEL_RU: dict[str, str] = {
    "weapon": "Оружие",
    "armor": "Броня",
    "shield": "Щит",
    "ring": "Кольцо",
    "amulet": "Амулет",
    "pants": "Поножи",
    "helmet": "Шлем",
    "gloves": "Перчатки",
    "boots": "Обувь",
    "cloak": "Плащ",
    "consumable": "Расходник",
    "craft_resource": "Ремесленный материал",
    "rune": "Руна",
    "grimoire": "Гримуар",
    "tome": "Фолиант",
    "orb": "Сфера",
    "focus": "Фокус",
    "dagger": "Кинжал",
}


def item_kind_label_ru(kind: str | None) -> str:
    if not kind:
        return ""
    k = str(kind).strip().lower()
    return ITEM_KIND_LABEL_RU.get(k, f"тип «{k}»")


_KIND_GEAR_ICON: dict[str, str] = {
    "weapon": "🗡️",
    "armor": "🦺",
    "pants": "👖",
    "helmet": "⛑️",
    "gloves": "🧤",
    "ring": "💍",
    "amulet": "📿",
    "shield": "🛡️",
    "dagger": "🔪",
    "grimoire": "📕",
    "tome": "📘",
    "orb": "🔮",
    "focus": "✨",
    "consumable": "🧪",
    "misc": "📦",
    "rune": "💎",
}


def gear_icon_for_item_data(data: dict[str, Any] | None) -> str:
    """Один эмодзи типа предмета для кнопок и карточек (kind / слот оружия)."""
    if not data:
        return "📦"
    kind = str(data.get("kind") or "").lower()
    if kind == "weapon":
        hand = str(data.get("hand") or "main").lower()
        if hand in ("off", "offhand", "left", "second"):
            return "🔪"
        return "🗡️"
    if kind in _KIND_GEAR_ICON:
        return _KIND_GEAR_ICON[kind]
    slot = resolve_equip_slot_for_item_data(data)
    if slot == "offhand":
        return "🛡️"
    if slot == "ring":
        return "💍"
    return "📦"
