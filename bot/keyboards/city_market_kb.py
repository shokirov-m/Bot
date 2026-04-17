"""Рынок городского хаба на 3 этаже."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row


def city_floor3_market_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    f = int(floor_number)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏪 Лавка торговца", callback_data=f"shp:main:{f}:m")],
            [InlineKeyboardButton(text="💰 Скупщик", callback_data=f"cty:mkt:{f}:scrap")],
            [InlineKeyboardButton(text="🏦 Банк (сейф)", callback_data=f"ecy:sfv:{f}:mkt")],
            [InlineKeyboardButton(text="⛪ Храм призыва", callback_data=f"cty:mkt:{f}:temple")],
            [InlineKeyboardButton(text="⬅ В город", callback_data=f"cty:mkt:{f}:hub")],
            menu_nav_button_row(),
        ],
    )


def temple_floor3_keyboard(floor_number: int, *, can_reroll: bool) -> InlineKeyboardMarkup:
    f = int(floor_number)
    row2: list[InlineKeyboardButton] = [
        InlineKeyboardButton(text="✅ Принять дар", callback_data=f"cty:mkt:{f}:temple_acc"),
    ]
    if can_reroll:
        row2.append(InlineKeyboardButton(text="🔁 Переброс", callback_data=f"cty:mkt:{f}:temple_rer"))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row2,
            [InlineKeyboardButton(text="⬅ На рынок", callback_data=f"cty:mkt:{f}:open")],
            menu_nav_button_row(),
        ],
    )

