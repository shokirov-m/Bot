"""
Городская кузница: заказы с эскроу и комиссией 5%% (хаб — этаж из workshop_constants).
"""

from __future__ import annotations

import copy
import html
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import character_repo, inventory_repo, workshop_order_repo
from game.crafting.recipes_data import (
    PROF_ALCHEMIST,
    PROF_BLACKSMITH,
    PROF_JEWELER,
    get_recipe_by_id,
    is_forge_instant,
)
from game.crafting.workshop_meta import get_workshop_state, prof_level, save_workshop_state
from game.floors import floor_data
from services import character_service, workshop_service
from game.crafting.workshop_constants import WORKSHOP_ORDERS_HUB_FLOOR
from game.items.craft_resources import RESOURCE_DEFS

_RARITY_GOLD: dict[str, int] = {
    "common": 20,
    "uncommon": 50,
    "rare": 120,
    "epic": 300,
    "legendary": 800,
    "mythic": 2000,
}


def _materials_gold_value(cost: dict[str, int]) -> int:
    t = 0
    for r, n in (cost or {}).items():
        t += int(n) * int(_RARITY_GOLD.get(str(r).lower(), 15))
    return t


_STAR_TO_GOLD: dict[int, int] = {
    1: 25,
    2: 55,
    3: 130,
    4: 320,
    5: 850,
    6: 2100,
}


def _craft_named_materials_gold(craft_cost: dict[str, int]) -> int:
    """Грубая оценка стоимости именованных материалов (⭐) для подсказки эскроу заказа."""
    t = 0
    for rid, n in (craft_cost or {}).items():
        d = RESOURCE_DEFS.get(str(rid)) or {}
        stars = max(1, min(6, int(d.get("stars") or 1)))
        per = int(_STAR_TO_GOLD.get(stars, 40))
        t += int(n) * per
    return t


def suggested_escrow_gold(character: Character, recipe_id: str) -> int:
    r = get_recipe_by_id(recipe_id)
    if r is None:
        return 0
    base = _materials_gold_value(dict(r.get("cost") or {})) + _craft_named_materials_gold(
        dict(r.get("craft_cost") or {}),
    )
    pl = max(
        prof_level(character, PROF_BLACKSMITH),
        prof_level(character, PROF_ALCHEMIST),
        prof_level(character, PROF_JEWELER),
    )
    return max(50, int(base * 1.5 + pl * 10))


def can_use_city_workshop_orders(character: Character) -> bool:
    if int(character.floor_number) != WORKSHOP_ORDERS_HUB_FLOOR:
        return False
    if floor_data.get_city_for_floor(int(character.floor_number)) is None:
        return False
    return prof_level(character, PROF_BLACKSMITH) >= 10


def can_post_order(character: Character) -> bool:
    """Разместить заказ может любой игрок в городе-хабе мастерской."""
    return int(character.floor_number) == WORKSHOP_ORDERS_HUB_FLOOR and floor_data.get_city_for_floor(
        int(character.floor_number),
    ) is not None


async def try_create_order(
    session: AsyncSession,
    character: Character,
    recipe_id: str,
    escrow_gross: int,
    order_type: str = "open",
) -> tuple[bool, str]:
    if not can_post_order(character):
        return False, f"Заказы доступны только в городе на {WORKSHOP_ORDERS_HUB_FLOOR} этаже."
    r = get_recipe_by_id(recipe_id)
    if r is None or is_forge_instant(r):
        return False, "Неверный рецепт для заказа."
    gross = max(1, int(escrow_gross))
    if int(character.gold) < gross:
        return False, "Недостаточно золота под эскроу."
    await character_repo.lock_character_row(session, character.id)
    character_service.add_gold(
        character,
        -gross,
        spend_for="Городская кузница: заказ в эскроу",
        spend_kind="workshop_order",
    )
    await workshop_order_repo.create_order(
        session,
        order_type=str(order_type)[:16],
        customer_char_id=int(character.id),
        recipe_id=str(recipe_id),
        qty=1,
        escrow_gold=gross,
        deadline_at=(
            (datetime.now(UTC) + timedelta(hours=24)).isoformat(timespec="seconds")
            if order_type == "rush"
            else None
        ),
    )
    await session.flush()
    return True, f"📋 Заказ размещён. Эскроу: <b>{gross:,}</b> 💰 (комиссия при выдаче мастеру)."


async def try_accept_order(
    session: AsyncSession,
    character: Character,
    order_id: int,
) -> tuple[bool, str]:
    if not can_use_city_workshop_orders(character):
        return False, f"Нужны: этаж {WORKSHOP_ORDERS_HUB_FLOOR} и кузнец ≥10."
    row = await workshop_order_repo.get_by_id(session, order_id)
    if row is None or str(row.get("status")) != "posted":
        return False, "Заказ недоступен."
    if int(row.get("customer_char_id") or 0) == int(character.id):
        return False, "Свой заказ принять нельзя."
    await character_repo.lock_character_row(session, character.id)
    await workshop_order_repo.set_accepted(session, order_id, int(character.id))
    await session.flush()
    return True, "Ты принял заказ. Сделай предмет и сдай."


async def try_complete_order(
    session: AsyncSession,
    character: Character,
    order_id: int,
) -> tuple[bool, str]:
    row = await workshop_order_repo.get_by_id(session, order_id)
    if row is None or str(row.get("status")) != "accepted":
        return False, "Заказ не в работе."
    if int(row.get("crafter_char_id") or 0) != int(character.id):
        return False, "Это не твой заказ."
    rid = str(row.get("recipe_id") or "")
    r = get_recipe_by_id(rid)
    if r is None:
        return False, "Рецепт удалён."
    gross = int(row.get("escrow_gold") or 0)
    payout = gross * 95 // 100
    cust_id = int(row.get("customer_char_id") or 0)
    await character_repo.lock_character_row(session, character.id)
    await character_repo.lock_character_row(session, cust_id)
    customer = await character_repo.get_by_id(session, cust_id)
    if customer is None:
        return False, "Заказчик не найден."
    slot = await inventory_repo.first_free_bag_slot(session, cust_id)
    if slot is None:
        return False, "У заказчика нет места в сумке — попроси освободить ячейку."
    pl = copy.deepcopy(r["result"])
    if str(r.get("profession")) == PROF_BLACKSMITH:
        pl = workshop_service.apply_blacksmith_forge_quality(character, pl)
    await inventory_repo.add_bag_item(session, cust_id, pl, bag_slot=slot)
    character_service.add_gold(character, payout, spend_for="Заказ мастерской", spend_kind="workshop_order")
    await workshop_order_repo.set_completed(session, order_id)
    ws = get_workshop_state(character)
    c = dict(ws.get("counters") or {})
    c["orders_completed"] = int(c.get("orders_completed", 0)) + 1
    c["gold_via_orders"] = int(c.get("gold_via_orders", 0)) + int(payout)
    ws["counters"] = c
    save_workshop_state(character, ws)
    await session.flush()
    nm = html.escape(str(pl.get("name", "Предмет")))
    return (
        True,
        f"✅ Заказ закрыт. Клиент получил {nm}. Твоё вознаграждение: <b>{payout:,}</b> 💰.",
    )


async def try_cancel_order(
    session: AsyncSession,
    character: Character,
    order_id: int,
) -> tuple[bool, str]:
    row = await workshop_order_repo.get_by_id(session, order_id)
    if row is None:
        return False, "Нет заказа."
    if int(row.get("customer_char_id") or 0) != int(character.id):
        return False, "Это не твой заказ."
    st = str(row.get("status"))
    if st != "posted":
        return False, "Уже принят мастером — отмена через поддержку."
    gross = int(row.get("escrow_gold") or 0)
    await character_repo.lock_character_row(session, character.id)
    character_service.add_gold(character, gross, spend_for="Возврат эскроу заказа", spend_kind="workshop_order")
    await workshop_order_repo.set_cancelled(session, order_id)
    await session.flush()
    return True, f"Эскроу возвращено: {gross:,} 💰."
