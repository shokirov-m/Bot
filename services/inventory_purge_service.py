"""
Одноразовые очистки инвентаря (флаг в AppGlobal).
"""

from __future__ import annotations

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from db.database import get_session_factory
from db.models.app_global import AppGlobal
from db.models.inventory import InventoryItem
from db.repository import inventory_repo
from game.combat import consumables as combat_consumables

_PURGE_STAMINA_RATIONS_FLAG = "stamina_rations_purged_v1"


async def purge_stamina_rations_if_needed() -> None:
    """Удалить из сумок все предметы с use_tag stamina_flat (один раз на базу)."""
    factory = get_session_factory()
    async with factory() as session:
        row = await session.get(AppGlobal, 1)
        if row is None:
            row = AppGlobal(id=1, payload={})
            session.add(row)
            await session.flush()
        p = dict(row.payload or {})
        if p.get(_PURGE_STAMINA_RATIONS_FLAG):
            return

        result = await session.execute(select(InventoryItem))
        items = list(result.scalars().all())
        removed = 0
        for it in items:
            if it.bag_slot is None:
                continue
            d = dict(it.item_data or {})
            if combat_consumables.normalize_combat_use_tag(d) != "stamina_flat":
                continue
            await inventory_repo.delete_inventory_item(session, it)
            removed += 1

        p[_PURGE_STAMINA_RATIONS_FLAG] = True
        row.payload = p
        flag_modified(row, "payload")
        await session.commit()
        if removed:
            logger.info("inventory_purge: удалено пайков стамины из сумок: {}", removed)
        else:
            logger.info("inventory_purge: пайков стамины не найдено, флаг выставлен.")
