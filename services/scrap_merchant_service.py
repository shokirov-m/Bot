"""
Скупщик на 3 этаже: выкуп предметов из сумки за золото (доля от «оценки»).
"""

from __future__ import annotations

import html
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.models.inventory import InventoryItem
from db.repository import inventory_repo
from services import character_service

SCRAP_FLOOR = 3
RARITY_MULT: dict[str, float] = {
    "common": 1.0,
    "uncommon": 1.15,
    "rare": 1.35,
    "epic": 1.6,
    "legendary": 2.0,
}


def scrap_gold_for_item_data(data: dict[str, Any]) -> int:
    """Цена скупки одного предмета (минимум 1)."""
    r = str(data.get("rarity") or "common").lower().strip()
    mul = RARITY_MULT.get(r, 1.0)
    atk = int(data.get("attack", data.get("atk", 0)) or 0)
    defe = int(data.get("defense", data.get("armor", 0)) or 0)
    kind = str(data.get("kind") or "")
    base = 4 + atk * 2 + defe * 2
    if kind == "rune" or data.get("rune_tier") is not None:
        base = max(base, 8 + int(data.get("rune_power", 0) or 0) * 2)
    if str(data.get("kind") or "") == "consumable":
        base = max(3, base // 2)
    return max(1, int(round(base * mul * 0.45)))


def format_scrap_menu_html(character: Character, items: list[InventoryItem]) -> str:
    lines = [
        "💰 <b>Скупщик</b>",
        "────────────",
        f"<i>Этаж {SCRAP_FLOOR}. Продай лут из сумки — золото сразу на руки.</i>",
        "",
    ]
    if not items:
        lines.append("<i>Сумка пуста — нечего продать.</i>")
        return "\n".join(lines)
    lines.append("<b>Предметы:</b>")
    for it in sorted(items, key=lambda x: (x.bag_slot or 0)):
        d = dict(it.item_data or {})
        nm = html.escape(str(d.get("name", "Предмет")))
        price = scrap_gold_for_item_data(d)
        slot = int(it.bag_slot) if it.bag_slot is not None else "?"
        lines.append(f"• [{slot}] {nm} — <b>{price}</b> 💰")
    return "\n".join(lines)


async def try_sell_bag_item_by_id(
    session: AsyncSession,
    character: Character,
    item_id: int,
    *,
    telegram_id: int | None = None,
    username: str | None = None,
    bot: Any = None,
) -> tuple[bool, str]:
    if int(character.floor_number) != SCRAP_FLOOR:
        return False, "Скупщик только на <b>3 этаже</b>."
    it = await inventory_repo.get_item_for_character(session, int(character.id), int(item_id))
    if it is None or it.is_equipped or it.bag_slot is None:
        return False, "Предмет не в сумке."
    data = dict(it.item_data or {})
    price = scrap_gold_for_item_data(data)
    nm = html.escape(str(data.get("name", "Предмет")))
    await inventory_repo.delete_inventory_item(session, it)
    character_service.add_gold(character, price)
    if telegram_id is not None and bot is not None:
        from services import anticheat_service

        await anticheat_service.record_gold_gain(
            session,
            character,
            telegram_id=telegram_id,
            username=username,
            gold_delta=price,
            bot=bot,
        )
    await session.flush()
    return True, f"Продано: <b>{nm}</b> за <b>{price}</b> 💰."
