"""Клавиатуры аукциона."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.auction_lot import AuctionLot
from game.economy.market import min_next_bid_for_lot


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


def bag_slots_for_auction_keyboard(slots_with_items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
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


def auction_lots_page_keyboard(
    lots: list[AuctionLot],
    *,
    page: int,
    total: int,
    page_size: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for lot in lots:
        name = str((lot.item_data or {}).get("name", f"Лот #{lot.id}"))[:22]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"#{lot.id} · {name}",
                    callback_data=f"auc:lot:{lot.id}",
                ),
            ],
        )
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"auc:browse:{page - 1}"))
    max_page = max(0, (total - 1) // page_size)
    if page < max_page:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"auc:browse:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ В аукцион", callback_data="auc:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lot_bid_keyboard(lot: AuctionLot) -> InlineKeyboardMarkup:
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
    rows.append([InlineKeyboardButton(text="⬅️ К списку", callback_data="auc:browse:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def auction_my_lots_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В аукцион", callback_data="auc:hub")],
            menu_nav_button_row(),
        ],
    )
