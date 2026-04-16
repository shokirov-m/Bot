"""Таверна: меню покупок."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from game.locations.tavern import TAVERN_MENU


def tavern_menu_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for o in TAVERN_MENU:
        label = f"{o.emoji} {o.name} — {o.price}💰"
        if len(label) > 64:
            label = label[:61] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"tvr:buy:{floor_number}:{o.key}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text="⬅ В город", callback_data=f"frg:city:{floor_number}")],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
