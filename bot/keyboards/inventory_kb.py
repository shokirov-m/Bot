"""Inline-клавиатуры инвентаря (сумка 20 слотов, экипировка)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.inventory import InventoryItem
from game.items import equipment as equip_meta
from utils.ui import item_bag_button_label

BAG_PAGE_SIZE = 8


def bag_tab_keyboard(items: list[InventoryItem], page: int) -> InlineKeyboardMarkup:
    sorted_items = sorted(items, key=lambda x: (x.bag_slot is None, x.bag_slot or 0))
    start = page * BAG_PAGE_SIZE
    chunk = sorted_items[start : start + BAG_PAGE_SIZE]
    rows: list[list[InlineKeyboardButton]] = []
    for it in chunk:
        label = item_bag_button_label(it.item_data, it.bag_slot)[:30]
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"inv:it:{it.id}:b:{page}")],
        )
    nav: list[InlineKeyboardButton] = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"inv:tab:bag:{page - 1}"))
    if start + BAG_PAGE_SIZE < len(sorted_items):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"inv:tab:bag:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⚔️ Экипировка", callback_data="inv:tab:eq")])
    rows.append([InlineKeyboardButton(text="✖ Закрыть", callback_data="inv:close")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def equipment_tab_keyboard(equipped: list[InventoryItem]) -> InlineKeyboardMarkup:
    by_slot: dict[str, InventoryItem] = {}
    for e in equipped:
        if e.equip_slot:
            by_slot[e.equip_slot] = e
    rows: list[list[InlineKeyboardButton]] = []
    for slot in equip_meta.EQUIP_ORDER:
        label_base = equip_meta.slot_label_ru(slot)
        it = by_slot.get(slot)
        if it is not None:
            name = str((it.item_data or {}).get("name", "?"))[:14]
            text = f"{label_base}: {name}"
            rows.append(
                [InlineKeyboardButton(text=text[:32], callback_data=f"inv:it:{it.id}:e:0")],
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{label_base}: —",
                        callback_data="inv:noop",
                    ),
                ],
            )
    rows.append([InlineKeyboardButton(text="🎒 Сумка", callback_data="inv:tab:bag:0")])
    rows.append([InlineKeyboardButton(text="✖ Закрыть", callback_data="inv:close")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def item_detail_keyboard(
    item_id: int,
    *,
    is_equipped: bool,
    can_equip: bool,
    from_bag: bool,
    bag_page: int,
    show_ration_eat: bool = False,
    show_bread_eat: bool = False,
) -> InlineKeyboardMarkup:
    back_cd = f"inv:tab:bag:{bag_page}" if from_bag else "inv:tab:eq"
    rows: list[list[InlineKeyboardButton]] = []
    if is_equipped:
        rows.append([InlineKeyboardButton(text="📥 Снять", callback_data=f"inv:uneq:{item_id}")])
    elif can_equip:
        rows.append([InlineKeyboardButton(text="📤 Надеть", callback_data=f"inv:eq:{item_id}")])
    if show_ration_eat:
        rows.append(
            [InlineKeyboardButton(text="🥖 Съесть (+2⚡)", callback_data=f"inv:eat:{item_id}:{bag_page}")],
        )
    if show_bread_eat:
        rows.append(
            [InlineKeyboardButton(text="🍞 Съесть (+HP)", callback_data=f"inv:bread:{item_id}:{bag_page}")],
        )
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=back_cd)])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
