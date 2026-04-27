"""Inline-клавиатуры инвентаря: хаб по категориям, сумка, экипировка."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.inventory import InventoryItem
from game.items import item_categories
from game.items import equipment as equip_meta
from game.items.equipment import RARITY_EMOJI, gear_icon_for_item_data
from utils.ui import item_bag_button_label

BAG_PAGE_SIZE = 8

# Сортировка сумки: редкость (легендарные сверху), затем номер ячейки.
_RARITY_SORT: dict[str, int] = {
    "mythic": 0,
    "legendary": 1,
    "epic": 2,
    "rare": 3,
    "uncommon": 4,
    "common": 5,
}


def _bag_sort_key(it: InventoryItem) -> tuple[int, int]:
    r = str((it.item_data or {}).get("rarity") or "common").lower()
    return (_RARITY_SORT.get(r, 99), it.bag_slot or 0)


def _equip_button_label(it: InventoryItem) -> str:
    data = it.item_data or {}
    gi = gear_icon_for_item_data(data)
    r = str(data.get("rarity") or "common").lower()
    em = RARITY_EMOJI.get(r, "⚪")
    name = str(data.get("name", "?"))[:10]
    return f"{gi}{em} {name}"[:32]


def inventory_hub_keyboard() -> InlineKeyboardMarkup:
    """Главный экран инвентаря — выбор категории сумки."""
    ic = item_categories
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗡️ Оружие", callback_data=f"inv:sec:{ic.INV_SEC_WEAPON}:0"),
                InlineKeyboardButton(text="🦺 Броня", callback_data=f"inv:sec:{ic.INV_SEC_ARMOR_BODY}:0"),
            ],
            [
                InlineKeyboardButton(text="⛑️ Шлем", callback_data=f"inv:sec:{ic.INV_SEC_HELMET}:0"),
                InlineKeyboardButton(text="👖 Поножи", callback_data=f"inv:sec:{ic.INV_SEC_PANTS}:0"),
            ],
            [
                InlineKeyboardButton(
                    text="🧤 Перчатки",
                    callback_data=f"inv:sec:{ic.INV_SEC_OTHER_GEAR}:0",
                ),
                InlineKeyboardButton(
                    text="💍 Кольца · амулет",
                    callback_data=f"inv:sec:{ic.INV_SEC_ACCESSORY}:0",
                ),
            ],
            [
                InlineKeyboardButton(text="🧪 Расходники", callback_data=f"inv:sec:{ic.INV_SEC_CONSUMABLE}:0"),
                InlineKeyboardButton(text="📦 Ресурсы", callback_data=f"inv:sec:{ic.INV_SEC_RESOURCE}:0"),
            ],
            [InlineKeyboardButton(text="⚔️ Что надето", callback_data="inv:tab:eq")],
            menu_nav_button_row(),
        ],
    )


def bag_tab_keyboard(
    items: list[InventoryItem],
    page: int,
    *,
    section: str,
) -> InlineKeyboardMarkup:
    """Список предметов сумки в секции: сортировка по редкости, по 8 на страницу."""
    ic = item_categories
    sec = section if section in ic.ALL_INV_SECTIONS else ic.INV_SEC_WEAPON
    sorted_items = sorted(
        [it for it in items if ic.item_data_matches_inv_section(it.item_data, sec)],
        key=_bag_sort_key,
    )
    start = page * BAG_PAGE_SIZE
    chunk = sorted_items[start : start + BAG_PAGE_SIZE]
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(chunk), 2):
        row: list[InlineKeyboardButton] = [
            InlineKeyboardButton(
                text=item_bag_button_label(chunk[i].item_data),
                callback_data=f"inv:it:{chunk[i].id}:b:{page}:{sec}",
            ),
        ]
        if i + 1 < len(chunk):
            row.append(
                InlineKeyboardButton(
                    text=item_bag_button_label(chunk[i + 1].item_data),
                    callback_data=f"inv:it:{chunk[i + 1].id}:b:{page}:{sec}",
                ),
            )
        rows.append(row)
    nav: list[InlineKeyboardButton] = []
    if start > 0:
        nav.append(
            InlineKeyboardButton(text="◀️", callback_data=f"inv:sec:{sec}:{page - 1}"),
        )
    if start + BAG_PAGE_SIZE < len(sorted_items):
        nav.append(
            InlineKeyboardButton(text="▶️", callback_data=f"inv:sec:{sec}:{page + 1}"),
        )
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅ Категории", callback_data="inv:hub")])
    rows.append([InlineKeyboardButton(text="⚔️ Что надето", callback_data="inv:tab:eq")])
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
            text = f"✓ {label_base}: {_equip_button_label(it)}"
            rows.append(
                [InlineKeyboardButton(text=text[:40], callback_data=f"inv:it:{it.id}:e:0")],
            )
        else:
            sec = item_categories.equip_slot_to_inv_section(slot)
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{label_base}: —",
                        callback_data=f"inv:sec:{sec}:0",
                    ),
                ],
            )
    rows.append([InlineKeyboardButton(text="🎒 Сумка", callback_data="inv:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def item_detail_keyboard(
    item_id: int,
    *,
    is_equipped: bool,
    can_equip: bool,
    from_bag: bool,
    bag_page: int,
    inv_section: str,
    show_ration_eat: bool = False,
    show_bread_eat: bool = False,
    source: str = "b",
) -> InlineKeyboardMarkup:
    """
    `source` — откуда пришёл пользователь к карточке предмета: `"b"` (сумка) или `"e"` (Что надето).
    Источник пробрасывается через колбэки eq/uneq, чтобы кнопка «Назад» возвращала туда же,
    откуда был сделан переход (учёт «последнего действия» от пользователя).
    """
    ic = item_categories
    sec = inv_section if inv_section in ic.ALL_INV_SECTIONS else ic.INV_SEC_WEAPON
    src = "e" if str(source).lower() == "e" else "b"
    back_cd = f"inv:sec:{sec}:{bag_page}" if from_bag else "inv:tab:eq"
    rows: list[list[InlineKeyboardButton]] = []
    if is_equipped:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✓ Снять в сумку",
                    callback_data=f"inv:uneq:{item_id}:{src}",
                ),
            ],
        )
    elif can_equip:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📤 Надеть",
                    callback_data=f"inv:eq:{item_id}:{sec}:{src}",
                ),
            ],
        )
    if show_ration_eat:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🥖 Съесть (+2⚡)",
                    callback_data=f"inv:eat:{item_id}:{bag_page}:{sec}",
                ),
            ],
        )
    if show_bread_eat:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🍞 Съесть (+HP)",
                    callback_data=f"inv:bread:{item_id}:{bag_page}:{sec}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=back_cd)])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
