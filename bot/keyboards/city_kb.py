"""Клавиатура городского хаба (кузница, таверна, экономика, призыв питомца)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.characters import pets as pets_mod


def city_hub_keyboard(floor_number: int, character: Character, *, locale: str = "ru") -> InlineKeyboardMarkup:
    loc = locale if locale in ("ru", "en") else "ru"
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
                ],
                [InlineKeyboardButton(text="🗺️ К этажу", callback_data=f"fl:{f}:return")],
                menu_nav_button_row(),
            ],
        )
    c1, c3, _r = pets_mod.city_summon_price_band(character)
    left = pets_mod.city_pet_pulls_remaining_today(character)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚒️ Кузница", callback_data=f"frg:main:{floor_number}")],
            [InlineKeyboardButton(text="🍺 Таверна", callback_data=f"tvr:open:{floor_number}")],
            [InlineKeyboardButton(text="🏪 Лавка", callback_data=f"shp:main:{floor_number}:c")],
            [
                InlineKeyboardButton(
                    text=t(loc, "city_pet_summon_1", cost=c1, left=left),
                    callback_data=f"cty:pet:1:{floor_number}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(loc, "city_pet_summon_3", cost=c3, left=left),
                    callback_data=f"cty:pet:3:{floor_number}",
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
