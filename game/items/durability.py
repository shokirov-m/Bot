"""
Прочность экипировки: износ после боёв, поломка при 0, починка за золото (кузница).

Стоимость: за каждые 2% недостающей прочности — по таблице редкости (текущие значения ~вдвое ниже прежних).
Mythic в ТЗ не был — взят двойной тариф легендарки.
"""

from __future__ import annotations

import html
import random
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from game.items.equipment.slots import resolve_equip_slot_for_item_data

DEFAULT_DURABILITY_MAX: int = 300

# За один «тик» в 2% от максимума прочности (в монетах); тариф снижен ~вдвое к исходному балансу
REPAIR_GOLD_PER_2_PERCENT: dict[str, int] = {
    "common": 2,
    "uncommon": 5,
    "rare": 10,
    "epic": 20,
    "legendary": 50,
    "mythic": 100,
}

_BAR_LEN = 14


def _mono_bar(current: int, maximum: int, length: int = _BAR_LEN) -> str:
    if maximum <= 0:
        maximum = 1
    current = max(0, min(current, maximum))
    filled = int(round((current / maximum) * length))
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def payload_supports_durability(data: dict[str, Any] | None) -> bool:
    if not data:
        return False
    kind = str(data.get("kind") or "").lower()
    if kind in ("consumable", "rune"):
        return False
    return resolve_equip_slot_for_item_data(data) is not None


def ensure_gear_durability_defaults(data: dict[str, Any]) -> None:
    """Инициализация прочности для снаряжения (на месте, мутирует data)."""
    if not payload_supports_durability(data):
        return
    dmax = int(data.get("durability_max") or 0)
    if dmax <= 0:
        dmax = DEFAULT_DURABILITY_MAX
        data["durability_max"] = dmax
    if "durability" not in data:
        data["durability"] = dmax
    else:
        data["durability"] = max(0, min(int(data["durability"] or 0), dmax))


def durability_pair(data: dict[str, Any] | None) -> tuple[int, int]:
    """(текущая, макс) без мутирования; для старых предметов — полная прочность."""
    if not data or not payload_supports_durability(data):
        return 0, 0
    dmax = int(data.get("durability_max") or 0)
    if dmax <= 0:
        dmax = DEFAULT_DURABILITY_MAX
    if "durability" not in data:
        return dmax, dmax
    dcur = int(data.get("durability") or 0)
    return max(0, min(dcur, dmax)), dmax


def item_is_broken(data: dict[str, Any] | None) -> bool:
    dcur, dmax = durability_pair(data)
    if dmax <= 0:
        return False
    return dcur <= 0


def repair_gold_cost(data: dict[str, Any] | None) -> int:
    """Стоимость полной починки предмета до максимума."""
    if not data or not payload_supports_durability(data):
        return 0
    dcur, dmax = durability_pair(data)
    if dcur >= dmax:
        return 0
    missing = dmax - dcur
    # Один «тик» тарифа = восстановление 2% от макс. прочности (в пунктах, с потолком)
    unit = max(1, (dmax * 2 + 99) // 100)
    steps = (missing + unit - 1) // unit
    rar = str(data.get("rarity") or "common").lower()
    per = REPAIR_GOLD_PER_2_PERCENT.get(rar, REPAIR_GOLD_PER_2_PERCENT["common"])
    return steps * per


def durability_wear_percent(data: dict[str, Any] | None) -> float:
    """Доля «поломки» 0–100%: 0 = как новый, 100 = сломан (нет прочности)."""
    if not data or not payload_supports_durability(data):
        return 0.0
    dcur, dmax = durability_pair(data)
    if dmax <= 0:
        return 0.0
    return max(0.0, min(100.0, 100.0 - (dcur / dmax) * 100.0))


def format_durability_line_html(data: dict[str, Any] | None) -> str:
    """Строка «Прочность» с полосой [████] и процентами (HTML)."""
    if not data or not payload_supports_durability(data):
        return ""
    dcur, dmax = durability_pair(data)
    pct = (dcur / dmax) * 100.0 if dmax > 0 else 0.0
    bar = _mono_bar(dcur, dmax)
    broken = dcur <= 0
    icon = "💀" if broken else "⚙️"
    warn = " <b>(СЛОМАНО)</b>" if broken else ""
    return (
        f'{icon} Прочность: <code>[{bar}]</code> '
        f"{dcur}/{dmax} ({pct:.0f}%){warn}"
    )


def apply_battle_wear_to_payload(data: dict[str, Any]) -> bool:
    """
    Списать 1–2% макс. прочности за бой. Мутирует data.
    Возвращает True, если предмет только что «сломался» (был >0, стал 0).
    """
    if not payload_supports_durability(data):
        return False
    ensure_gear_durability_defaults(data)
    dmax = int(data["durability_max"])
    dcur = int(data.get("durability", dmax))
    if dcur <= 0:
        return False
    pct_roll = random.choice((1, 2))
    loss = max(1, (dmax * pct_roll + 99) // 100)
    new = max(0, dcur - loss)
    data["durability"] = new
    return dcur > 0 and new <= 0


async def wear_equipped_items_after_battle(session: AsyncSession, character_id: int) -> str:
    """
    Износ всех надетых предметов с прочностью. Возвращает HTML-суффикс для экрана победы
    (если что-то сломалось).
    """
    from db.repository import inventory_repo  # avoid circular import with inventory_repo

    broken_names: list[str] = []
    items = await inventory_repo.list_equipped_items(session, character_id)
    changed = False
    for it in items:
        data = dict(it.item_data or {})
        if not payload_supports_durability(data):
            continue
        if apply_battle_wear_to_payload(data):
            broken_names.append(html.escape(str(data.get("name", "?"))))
        it.item_data = data
        changed = True
    if changed:
        await session.flush()
    if broken_names:
        return (
            "\n💔 <b>Сломалось:</b> "
            + ", ".join(broken_names)
            + ". Почини в <b>кузнице</b> города."
        )
    return ""


async def total_repair_cost_equipped(session: AsyncSession, character_id: int) -> int:
    from db.repository import inventory_repo  # avoid circular import with inventory_repo

    total = 0
    for it in await inventory_repo.list_equipped_items(session, character_id):
        data = dict(it.item_data or {})
        if not payload_supports_durability(data):
            continue
        ensure_gear_durability_defaults(data)
        total += repair_gold_cost(data)
    return total
