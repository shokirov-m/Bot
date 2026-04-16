"""Клавиатура городского хаба (кузница, таверна, экономика)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row


def city_hub_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚒️ Кузница", callback_data=f"frg:main:{floor_number}")],
            [InlineKeyboardButton(text="🍺 Таверна", callback_data=f"tvr:open:{floor_number}")],
            [InlineKeyboardButton(text="🏪 Лавка", callback_data=f"shp:main:{floor_number}:c")],
            [
                InlineKeyboardButton(text="⚔️ Стражник", callback_data=f"cty:{floor_number}:view"),
                InlineKeyboardButton(text="💸 Экономика", callback_data=f"ecy:hub:{floor_number}"),
            ],
            [InlineKeyboardButton(text="🗺️ К этажу", callback_data=f"fl:{floor_number}:return")],
            menu_nav_button_row(),
        ],
    )
