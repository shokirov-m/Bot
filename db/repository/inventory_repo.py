"""Запросы к инвентарю."""

from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.inventory import InventoryItem
from game.items import equipment as equip_meta


async def get_bag_item_at_slot(
    session: AsyncSession,
    character_id: int,
    bag_slot: int,
) -> InventoryItem | None:
    """Предмет в сумке в указанной ячейке 0..19."""
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == character_id,
            InventoryItem.is_equipped.is_(False),
            InventoryItem.bag_slot == bag_slot,
        ),
    )
    return result.scalar_one_or_none()


async def list_bag_items(session: AsyncSession, character_id: int) -> list[InventoryItem]:
    """Предметы только в сумке (не в экипировке)."""
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == character_id,
            InventoryItem.is_equipped.is_(False),
            InventoryItem.bag_slot.isnot(None),
        ),
    )
    return list(result.scalars().all())


async def list_equipped_items(session: AsyncSession, character_id: int) -> list[InventoryItem]:
    """Все надетые предметы персонажа."""
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == character_id,
            InventoryItem.is_equipped.is_(True),
        ),
    )
    items = list(result.scalars().all())
    order = {s: i for i, s in enumerate(equip_meta.EQUIP_ORDER)}
    items.sort(key=lambda it: order.get(it.equip_slot or "", 99))
    return items


async def get_item_for_character(
    session: AsyncSession,
    character_id: int,
    item_id: int,
) -> InventoryItem | None:
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id,
            InventoryItem.character_id == character_id,
        ),
    )
    return result.scalar_one_or_none()


async def get_equipped_in_slot(
    session: AsyncSession,
    character_id: int,
    equip_slot: str,
) -> InventoryItem | None:
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == character_id,
            InventoryItem.is_equipped.is_(True),
            InventoryItem.equip_slot == equip_slot,
        ),
    )
    return result.scalar_one_or_none()


async def first_free_bag_slot(session: AsyncSession, character_id: int) -> int | None:
    """Первый свободный индекс 0..19 или None если сумка полна."""
    items = await list_bag_items(session, character_id)
    used = {i.bag_slot for i in items if i.bag_slot is not None}
    for s in range(20):
        if s not in used:
            return s
    return None


async def equip_item_from_bag(session: AsyncSession, item: InventoryItem) -> str | None:
    """
    Надеть предмет из сумки. При занятом слоте текущая вещь уходит в сумку.
    Возвращает текст ошибки по-русски или None при успехе.
    """
    data = item.item_data or {}
    slot = equip_meta.equip_slot_for_kind(data.get("kind"))
    if not slot:
        return "Этот предмет нельзя экипировать."
    if item.is_equipped:
        return "Уже надето."

    existing = await get_equipped_in_slot(session, item.character_id, slot)
    if existing is not None:
        free = await first_free_bag_slot(session, item.character_id)
        if free is None:
            return "Сумка полна. Освободи ячейку, чтобы снять текущую вещь."
        existing.is_equipped = False
        existing.equip_slot = None
        existing.bag_slot = free

    item.is_equipped = True
    item.equip_slot = slot
    item.bag_slot = None
    await session.flush()
    return None


async def unequip_item(session: AsyncSession, item: InventoryItem) -> str | None:
    """Снять предмет в сумку. Ошибка, если сумка полна."""
    if not item.is_equipped:
        return "Предмет не в экипировке."
    free = await first_free_bag_slot(session, item.character_id)
    if free is None:
        return "Сумка полна — нечего освобождать под снятую вещь."
    item.is_equipped = False
    item.equip_slot = None
    item.bag_slot = free
    await session.flush()
    return None


async def add_starter_equipped_weapon(
    session: AsyncSession,
    character_id: int,
    *,
    item_data: dict,
) -> InventoryItem:
    """Стартовое оружие сразу в слоте weapon."""
    row = InventoryItem(
        character_id=character_id,
        is_equipped=True,
        equip_slot="weapon",
        bag_slot=None,
        item_data=item_data,
    )
    session.add(row)
    await session.flush()
    return row


async def get_equipped_weapon(session: AsyncSession, character_id: int) -> InventoryItem | None:
    """Надетое оружие."""
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == character_id,
            InventoryItem.is_equipped.is_(True),
            InventoryItem.equip_slot == "weapon",
        ),
    )
    return result.scalar_one_or_none()


async def delete_inventory_item(session: AsyncSession, item: InventoryItem) -> None:
    await session.delete(item)


async def pick_random_bag_item(session: AsyncSession, character_id: int) -> InventoryItem | None:
    """Случайный предмет из сумки или None."""
    items = await list_bag_items(session, character_id)
    if not items:
        return None
    return random.choice(items)


async def add_bag_item(
    session: AsyncSession,
    character_id: int,
    item_data: dict,
    *,
    bag_slot: int | None = None,
) -> InventoryItem:
    """Добавить предмет в сумку (bag_slot можно назначить позже)."""
    row = InventoryItem(
        character_id=character_id,
        is_equipped=False,
        equip_slot=None,
        bag_slot=bag_slot,
        item_data=item_data,
    )
    session.add(row)
    await session.flush()
    return row
