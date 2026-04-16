"""Клавиатуры аукциона."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.auction_lot import AuctionLot
from game.economy.market import min_next_bid_for_lot
from game.items import item_categories


def auction_hub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Выставить", callback_data="auc:create")],
            [InlineKeyboardButton(text="💰 Сделать ставку", callback_data="auc:browse:0")],
            [InlineKeyboardButton(text="📋 Мои лоты", callback_data="auc:my")],
            menu_nav_button_row(),
        ],
    )


def auction_cancel_create_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="auc:hub")],
        ],
    )


def auction_bag_category_row(*, selected: str) -> list[InlineKeyboardButton]:
    """Фильтр предметов при выставлении (короткие callback_data)."""
    opts = [
        (item_categories.BAG_CAT_ALL, "Все"),
        (item_categories.BAG_CAT_EQUIP, "⚔️ Экип"),
        (item_categories.BAG_CAT_USE, "🧪 Расх."),
        (item_categories.BAG_CAT_OTHER, "📦 Прочее"),
    ]
    row: list[InlineKeyboardButton] = []
    for code, label in opts:
        mark = f"·{label}" if code == selected else label
        row.append(InlineKeyboardButton(text=mark[:12], callback_data=f"auc:create:{code}"))
    return row


def bag_slots_for_auction_keyboard(
    slots_with_items: list[tuple[int, str]],
    *,
    bag_cat: str = item_categories.BAG_CAT_ALL,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(auction_bag_category_row(selected=bag_cat))
    row: list[InlineKeyboardButton] = []
    for slot, label in slots_with_items:
        row.append(InlineKeyboardButton(text=label[:40], callback_data=f"auc:pick:{slot}"))
        if len(row) >= 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="auc:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def auction_browse_category_keyboard(*, page: int, selected: str) -> list[InlineKeyboardButton]:
    opts = [
        (item_categories.BAG_CAT_ALL, "Все"),
        (item_categories.BAG_CAT_EQUIP, "⚔️"),
        (item_categories.BAG_CAT_USE, "🧪"),
        (item_categories.BAG_CAT_OTHER, "📦"),
    ]
    return [
        InlineKeyboardButton(
            text=("·" + label) if code == selected else label,
            callback_data=f"auc:browse:{page}:{code}",
        )
        for code, label in opts
    ]


def auction_lots_page_keyboard(
    lots: list[AuctionLot],
    *,
    page: int,
    total: int,
    page_size: int,
    category: str = item_categories.BAG_CAT_ALL,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(auction_browse_category_keyboard(page=page, selected=category))
    for lot in lots:
        name = str((lot.item_data or {}).get("name", f"Лот #{lot.id}"))[:22]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"#{lot.id} · {name}",
                    callback_data=f"auc:lot:{lot.id}:{page}:{category}",
                ),
            ],
        )
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"auc:browse:{page - 1}:{category}"))
    max_page = max(0, (total - 1) // page_size)
    if page < max_page:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"auc:browse:{page + 1}:{category}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ В аукцион", callback_data="auc:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lot_bid_keyboard(
    lot: AuctionLot,
    *,
    browse_page: int = 0,
    browse_cat: str = item_categories.BAG_CAT_ALL,
) -> InlineKeyboardMarkup:
    m = min_next_bid_for_lot(lot)
    amounts: list[int] = [m]
    for d in (50, 200, 1000, 5000):
        x = m + d
        if x > m and x not in amounts:
            amounts.append(x)
    amounts = sorted(set(amounts))[:5]
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for a in amounts:
        row.append(InlineKeyboardButton(text=f"{a} 💰", callback_data=f"auc:bid:{lot.id}:{a}"))
        if len(row) >= 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ К списку",
                callback_data=f"auc:browse:{browse_page}:{browse_cat}",
            ),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lot_seller_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛑 Снять лот", callback_data=f"auc:cnl:{lot_id}"),
                InlineKeyboardButton(text="💠 Новая цена", callback_data=f"auc:repr:{lot_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ Мои лоты", callback_data="auc:my")],
            menu_nav_button_row(),
        ],
    )


def auction_reprice_cancel_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"auc:lot:{lot_id}:0:{item_categories.BAG_CAT_ALL}")],
        ],
    )


def auction_my_lots_keyboard(active_lot_ids: list[int] | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if active_lot_ids:
        for lid in active_lot_ids[:8]:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"⚙️ Лот #{lid}",
                        callback_data=f"auc:lot:{lid}:0:{item_categories.BAG_CAT_ALL}",
                    ),
                ],
            )
    rows.append([InlineKeyboardButton(text="⬅️ В аукцион", callback_data="auc:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
