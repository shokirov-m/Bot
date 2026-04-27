"""Клавиатура городского хаба (кузница, таверна, экономика, призыв питомца)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character


def city_hub_keyboard(
    floor_number: int,
    character: Character,
    *,
    locale: str = "ru",
) -> InlineKeyboardMarkup:
    _ = (character, locale)  # API сохранён для совместимости с вызовами
    f = int(floor_number)
    if f == 3:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⚒️ Кузница", callback_data=f"frg:main:{f}")],
                [InlineKeyboardButton(text="🍺 Таверна", callback_data=f"tvr:open:{f}")],
                [InlineKeyboardButton(text="🏛️ Рынок", callback_data=f"cty:mkt:{f}:open")],
                [
                    InlineKeyboardButton(text="⚔️ Стражник", callback_data=f"cty:{f}:view"),
                    InlineKeyboardButton(text="📜 Писарь", callback_data=f"cty:f3npc:scribe:{f}"),
                ],
                [
                    InlineKeyboardButton(text="🌿 Мара", callback_data=f"cty:f3npc:herb:{f}"),
                    InlineKeyboardButton(text="🐾 Животновод", callback_data=f"cty:pet_hub:{f}"),
                ],
                [InlineKeyboardButton(text="🗺️ К этажу", callback_data=f"fl:{f}:return")],
                menu_nav_button_row(),
            ],
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚒️ Кузница", callback_data=f"frg:main:{floor_number}")],
            [InlineKeyboardButton(text="🍺 Таверна", callback_data=f"tvr:open:{floor_number}")],
            [InlineKeyboardButton(text="🏪 Лавка", callback_data=f"shp:main:{floor_number}:c")],
            [
                InlineKeyboardButton(
                    text="🐾 Животновод",
                    callback_data=f"cty:pet_hub:{floor_number}",
                ),
            ],
            [
                InlineKeyboardButton(text="⚔️ Стражник", callback_data=f"cty:{floor_number}:view"),
                InlineKeyboardButton(text="💸 Экономика", callback_data=f"ecy:hub:{floor_number}"),
            ],
            [InlineKeyboardButton(text="🗺️ К этажу", callback_data=f"fl:{floor_number}:return")],
            menu_nav_button_row(),
        ],
    )
