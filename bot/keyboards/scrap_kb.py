"""Клавиатура скупщика (этаж 3): продать предмет по id."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.inventory import InventoryItem


def scrap_merchant_keyboard(items: list[InventoryItem]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for it in sorted(items, key=lambda x: (x.bag_slot or 0)):
        d = dict(it.item_data or {})
        nm = str(d.get("name", "Предмет"))
        if len(nm) > 22:
            nm = nm[:19] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"💰 {nm}",
                    callback_data=f"scr:{int(it.id)}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅️ К этажу", callback_data="scr:back")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
