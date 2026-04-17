"""Inline-клавиатуры инвентаря (сумка без лимита слотов, экипировка)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.inventory import InventoryItem
from game.items import equipment as equip_meta
from game.items.equipment import RARITY_EMOJI, gear_icon_for_item_data
from game.items import item_categories
from utils.ui import item_bag_button_label

BAG_PAGE_SIZE = 10

# Сортировка сумки: редкость (легендарные сверху), затем номер ячейки.
_RARITY_SORT: dict[str, int] = {
    "legendary": 0,
    "epic": 1,
    "rare": 2,
    "uncommon": 3,
    "common": 4,
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


def bag_category_filter_row(
    page: int,
    selected: str,
    *,
    slot_target: str | None = None,
) -> list[InlineKeyboardButton]:
    opts = [
        (item_categories.BAG_CAT_ALL, "Все"),
        (item_categories.BAG_CAT_EQUIP, "⚔️ Экип"),
        (item_categories.BAG_CAT_USE, "🧪 Расх."),
        (item_categories.BAG_CAT_OTHER, "📦 Прочее"),
    ]
    prefix = f"inv:sb:{slot_target}" if slot_target else "inv:tab:bag"
    return [
        InlineKeyboardButton(
            text=(f"·{label}") if code == selected else label,
            callback_data=f"{prefix}:{page}:{code}",
        )
        for code, label in opts
    ]


def bag_tab_keyboard(
    items: list[InventoryItem],
    page: int,
    *,
    bag_cat: str = item_categories.BAG_CAT_ALL,
    slot_target: str | None = None,
) -> InlineKeyboardMarkup:
    sorted_items = sorted(
        [
            it
            for it in items
            if item_categories.item_data_matches_bag_category(it.item_data, bag_cat)
            and item_categories.item_data_matches_equip_slot(it.item_data, slot_target)
        ],
        key=_bag_sort_key,
    )
    start = page * BAG_PAGE_SIZE
    chunk = sorted_items[start : start + BAG_PAGE_SIZE]
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(bag_category_filter_row(page, bag_cat, slot_target=slot_target))
    nav_prefix = f"inv:sb:{slot_target}" if slot_target else "inv:tab:bag"
    it_suffix = f":{slot_target}" if slot_target else ""
    for i in range(0, len(chunk), 2):
        row: list[InlineKeyboardButton] = [
            InlineKeyboardButton(
                text=item_bag_button_label(chunk[i].item_data),
                callback_data=f"inv:it:{chunk[i].id}:b:{page}:{bag_cat}{it_suffix}",
            ),
        ]
        if i + 1 < len(chunk):
            row.append(
                InlineKeyboardButton(
                    text=item_bag_button_label(chunk[i + 1].item_data),
                    callback_data=f"inv:it:{chunk[i + 1].id}:b:{page}:{bag_cat}{it_suffix}",
                ),
            )
        rows.append(row)
    nav: list[InlineKeyboardButton] = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"{nav_prefix}:{page - 1}:{bag_cat}"))
    if start + BAG_PAGE_SIZE < len(sorted_items):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"{nav_prefix}:{page + 1}:{bag_cat}"))
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
            text = f"✓ {label_base}: {_equip_button_label(it)}"
            rows.append(
                [InlineKeyboardButton(text=text[:40], callback_data=f"inv:it:{it.id}:e:0")],
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{label_base}: —",
                        callback_data=f"inv:sb:{slot}:0:{item_categories.BAG_CAT_EQUIP}",
                    ),
                ],
            )
    rows.append(
        [InlineKeyboardButton(text="🎒 Сумка", callback_data=f"inv:tab:bag:0:{item_categories.BAG_CAT_ALL}")],
    )
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
    bag_cat: str = item_categories.BAG_CAT_ALL,
    show_ration_eat: bool = False,
    show_bread_eat: bool = False,
    slot_target: str | None = None,
) -> InlineKeyboardMarkup:
    if from_bag and slot_target:
        back_cd = f"inv:sb:{slot_target}:{bag_page}:{bag_cat}"
    elif from_bag:
        back_cd = f"inv:tab:bag:{bag_page}:{bag_cat}"
    else:
        back_cd = "inv:tab:eq"
    rows: list[list[InlineKeyboardButton]] = []
    if is_equipped:
        rows.append([InlineKeyboardButton(text="✓ Снять в сумку", callback_data=f"inv:uneq:{item_id}")])
    elif can_equip:
        rows.append([InlineKeyboardButton(text="📤 Надеть", callback_data=f"inv:eq:{item_id}")])
    if show_ration_eat:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🥖 Съесть (+2⚡)",
                    callback_data=f"inv:eat:{item_id}:{bag_page}:{bag_cat}",
                ),
            ],
        )
    if show_bread_eat:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🍞 Съесть (+HP)",
                    callback_data=f"inv:bread:{item_id}:{bag_page}:{bag_cat}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=back_cd)])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
