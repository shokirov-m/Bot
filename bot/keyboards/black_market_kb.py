"""Клавиатуры чёрного рынка «Тени Башни»."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from game.mercenaries.market_hub import LOCATIONS


def market_hub_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🐸 Площадь лотов (Жабс)", callback_data="bm:jabs")],
    ]
    for loc in LOCATIONS[1:]:
        rows.append([
            InlineKeyboardButton(
                text=f"📍 {loc.title_ru}",
                callback_data=f"bm:loc:{loc.key}",
            ),
        ])
    rows.append([InlineKeyboardButton(text="🗺️ К этажу", callback_data="bm:back_floor")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def jabs_lots_keyboard(n_lots: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(n_lots):
        rows.append([
            InlineKeyboardButton(text=f"Лот #{i + 1}", callback_data=f"bm:buy:{i}"),
        ])
    rows.append([InlineKeyboardButton(text="⬅ В хаб", callback_data="bm:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def location_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ В хаб", callback_data="bm:hub")],
            menu_nav_button_row(),
        ],
    )
