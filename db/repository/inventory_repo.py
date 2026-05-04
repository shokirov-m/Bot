"""Запросы к инвентарю."""

from __future__ import annotations

import copy
import random

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.inventory import InventoryItem
from game.balance import BAG_MAX_SLOT_INDEX
from game.items import durability as durability_mod
from game.items.equipment.defaults import apply_item_payload_defaults
from game.items.equipment.slots import (
    item_is_two_handed,
    resolve_equip_slot_for_item_data,
    ring_slot_is_explicit,
)
from game.items import equipment as equip_meta
from game.items import item_categories as ic


# Поля, наличие которых делает предмет "нестакаемым" (заточка/прочность/руны).
_NON_STACK_DATA_KEYS: tuple[str, ...] = (
    "enchant",
    "enchant_level",
    "enchant_tier",
    "durability",
    "durability_max",
    "runes",
    "rune_slots",
    "sockets",
)


def _is_stackable_kind(data: dict) -> bool:
    """True если предмет относится к Ресурсам или Расходникам и не имеет per-instance состояния."""
    cat = ic.bag_category_for_item_data(data)
    if cat not in (ic.BAG_CAT_USE, ic.BAG_CAT_OTHER):
        return False
    for key in _NON_STACK_DATA_KEYS:
        if key in data and data.get(key) not in (None, 0, "", [], {}):
            return False
    return True


def _stack_signature(data: dict) -> tuple:
    """Идентичность для стакания: kind+name+rarity+tier+use_tag+use_value (+item_id если есть)."""
    return (
        str(data.get("kind") or ""),
        str(data.get("name") or ""),
        str(data.get("rarity") or ""),
        int(data.get("tier") or 0),
        str(data.get("use_tag") or ""),
        int(data.get("use_value") or 0),
        str(data.get("item_id") or data.get("key") or ""),
        str(data.get("resource_id") or ""),
    )


async def get_bag_item_at_slot(
    session: AsyncSession,
    character_id: int,
    bag_slot: int,
) -> InventoryItem | None:
    """Предмет в сумке в указанной ячейке."""
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


async def _pick_ring_equip_slot(session: AsyncSession, character_id: int, data: dict) -> str:
    """Без ring_slot в данных: первый пустой из ring / ring2, иначе смена кольца I."""
    if ring_slot_is_explicit(data):
        s = resolve_equip_slot_for_item_data(data)
        return s if s in ("ring", "ring2") else "ring"
    r1 = await get_equipped_in_slot(session, character_id, "ring")
    r2 = await get_equipped_in_slot(session, character_id, "ring2")
    if r1 is None:
        return "ring"
    if r2 is None:
        return "ring2"
    return "ring"


async def first_free_bag_slot(session: AsyncSession, character_id: int) -> int | None:
    """Первый свободный индекс сумки (лимита по количеству ячеек нет)."""
    items = await list_bag_items(session, character_id)
    used = {i.bag_slot for i in items if i.bag_slot is not None}
    n = 0
    while n in used:
        n += 1
        if n > BAG_MAX_SLOT_INDEX:
            return None
    return n


async def equip_item_from_bag(session: AsyncSession, item: InventoryItem) -> str | None:
    """
    Надеть предмет из сумки. При занятом слоте текущая вещь уходит в сумку.
    Двуручное в основной руке освобождает вторую руку; при активном двуручнике вторую руку занять нельзя.
    Возвращает текст ошибки по-русски или None при успехе.
    """
    data = dict(item.item_data or {})
    apply_item_payload_defaults(data)
    durability_mod.ensure_gear_durability_defaults(data)
    item.item_data = data
    slot = resolve_equip_slot_for_item_data(data)
    if not slot:
        return "Этот предмет нельзя экипировать."
    if item.is_equipped:
        return "Уже надето."
    cid = int(item.character_id)

    if str(data.get("kind") or "").lower() == "ring":
        slot = await _pick_ring_equip_slot(session, cid, data)

    if slot == "offhand":
        main_w = await get_equipped_weapon(session, cid)
        if main_w is not None and item_is_two_handed(dict(main_w.item_data or {})):
            return "Двуручное оружие в основной руке — сначала сними его или смени на одноручное."

    if slot == "weapon" and item_is_two_handed(data):
        off_i = await get_equipped_in_slot(session, cid, "offhand")
        if off_i is not None:
            free = await first_free_bag_slot(session, cid)
            if free is None:
                return "Сумка полна. Освободи ячейку, чтобы снять предмет со второй руки перед двуручником."
            off_i.is_equipped = False
            off_i.equip_slot = None
            off_i.bag_slot = free

    existing = await get_equipped_in_slot(session, cid, slot)
    if existing is not None:
        free = await first_free_bag_slot(session, cid)
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
    data = copy.deepcopy(item_data)
    apply_item_payload_defaults(data)
    durability_mod.ensure_gear_durability_defaults(data)
    row = InventoryItem(
        character_id=character_id,
        is_equipped=True,
        equip_slot="weapon",
        bag_slot=None,
        item_data=data,
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


async def wipe_inventory(session: AsyncSession, character_id: int) -> int:
    """Удалить все предметы персонажа (и в сумке, и в экипировке).
    Возвращает количество удалённых записей."""
    result = await session.execute(
        delete(InventoryItem).where(InventoryItem.character_id == character_id),
    )
    await session.flush()
    return result.rowcount or 0


async def wipe_all_inventories(session: AsyncSession) -> int:
    """Удалить ВСЕ предметы у ВСЕХ персонажей.
    Возвращает количество удалённых записей."""
    result = await session.execute(delete(InventoryItem))
    await session.flush()
    return result.rowcount or 0


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
) -> InventoryItem | None:
    """
    Добавить предмет в сумку.
    Для ресурсов/расходников — стакуется в существующую запись (`item_data["count"] += n`),
    иначе создаётся новая запись (снаряжение, заточка, руны и т.п.).
    Если стакаемый предмет приходит без `bag_slot` и в сумке нет существующего стака —
    автоматически берётся первый свободный слот, чтобы он не оказался "невидимым".
    Если свободных слотов нет (лимит BAG_MAX_SLOT_INDEX), возвращает None — не создаёт запись с bag_slot=NULL.
    """
    data = copy.deepcopy(item_data)
    apply_item_payload_defaults(data)
    durability_mod.ensure_gear_durability_defaults(data)
    if _is_stackable_kind(data):
        existing = await find_stack(session, character_id, data)
        if existing is not None:
            ed = dict(existing.item_data or {})
            add_n = max(1, int(data.get("count") or 1))
            ed["count"] = max(1, int(ed.get("count") or 1)) + add_n
            existing.item_data = ed
            await session.flush()
            return existing
        if "count" not in data:
            data["count"] = 1
        if bag_slot is None:
            bag_slot = await first_free_bag_slot(session, character_id)
        if bag_slot is None:
            return None
    row = InventoryItem(
        character_id=character_id,
        is_equipped=False,
        equip_slot=None,
        bag_slot=bag_slot,
        item_data=data,
    )
    session.add(row)
    await session.flush()
    return row


async def find_stack(
    session: AsyncSession,
    character_id: int,
    item_data: dict,
) -> InventoryItem | None:
    """Поиск существующего стака с такой же сигнатурой в сумке."""
    if not _is_stackable_kind(item_data):
        return None
    target_sig = _stack_signature(item_data)
    bag = await list_bag_items(session, character_id)
    for it in bag:
        d = it.item_data or {}
        if not _is_stackable_kind(d):
            continue
        if _stack_signature(d) == target_sig:
            return it
    return None


async def consume_one_from_stack(
    session: AsyncSession,
    item: InventoryItem,
) -> int:
    """
    Списать одну единицу из стака.
    Если count > 1 — уменьшаем count на 1; иначе удаляем запись целиком.
    Возвращает оставшееся количество (0 = запись удалена).
    """
    data = dict(item.item_data or {})
    cur = max(1, int(data.get("count") or 1))
    if cur > 1:
        data["count"] = cur - 1
        item.item_data = data
        await session.flush()
        return cur - 1
    await session.delete(item)
    await session.flush()
    return 0


def stack_count(item: InventoryItem) -> int:
    """Текущее количество в стаке (для нестакаемых — всегда 1)."""
    d = item.item_data or {}
    if not _is_stackable_kind(d):
        return 1
    return max(1, int(d.get("count") or 1))


async def consolidate_bag_stacks(session: AsyncSession, character_id: int) -> int:
    """
    Объединить уже лежащие в сумке стакаемые предметы с одинаковой сигнатурой.
    Полезно для предметов, попавших в сумку до включения авто-стакинга.
    Возвращает количество удалённых (свернутых) записей.
    """
    bag = await list_bag_items(session, character_id)
    groups: dict[tuple, list[InventoryItem]] = {}
    for it in bag:
        d = it.item_data or {}
        if not _is_stackable_kind(d):
            continue
        sig = _stack_signature(d)
        groups.setdefault(sig, []).append(it)
    removed = 0
    for sig, items in groups.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda x: (x.bag_slot if x.bag_slot is not None else 1 << 30, int(x.id)))
        keeper = items[0]
        kdata = dict(keeper.item_data or {})
        total = max(1, int(kdata.get("count") or 1))
        for extra in items[1:]:
            ed = extra.item_data or {}
            total += max(1, int(ed.get("count") or 1))
            await session.delete(extra)
            removed += 1
        kdata["count"] = total
        keeper.item_data = kdata
    if removed:
        await session.flush()
    return removed
