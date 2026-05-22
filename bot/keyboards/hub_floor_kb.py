"""Клавиатуры независимых хаб-этажей (библиотека, города)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.locations import hub_floors as hf
from bot.keyboards.city_kb import city_hub_keyboard
from bot.keyboards.grimoire_library_kb import library_hub_keyboard


def hub_travel_menu_keyboard(character: Character) -> InlineKeyboardMarkup:
    """Меню «Локации»: переход на хаб-этажи."""
    rows: list[list[InlineKeyboardButton]] = []
    if hf.library_hub_accessible(character):
        rows.append(
            [
                InlineKeyboardButton(
                    text="📚 Библиотека гримуаров",
                    callback_data=f"hub:go:{hf.LIBRARY_HUB_FLOOR}",
                ),
            ],
        )
    for fl, em, name in hf.list_accessible_city_hub_floors(character):
        lbl = f"{em} {name}"[:36]
        rows.append(
            [InlineKeyboardButton(text=lbl, callback_data=f"hub:go:{fl}")],
        )
    rows.append([InlineKeyboardButton(text="◀️ Меню", callback_data="mnu:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def library_hub_screen_keyboard(character: Character) -> InlineKeyboardMarkup:
    """Экран библиотеки на хаб-этаже — единая клавиатура с lib:open."""
    return library_hub_keyboard(character, hf.LIBRARY_HUB_FLOOR)


def city_hub_screen_keyboard(
    character: Character,
    *,
    locale: str = "ru",
) -> InlineKeyboardMarkup:
    fl = int(character.floor_number)
    city = hf.city_for_hub_floor(fl)
    if city is None:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🗼 В башню", callback_data="hub:back:tower")],
            ],
        )
    kb = city_hub_keyboard(fl, character, locale=locale)
    extra = [[InlineKeyboardButton(text="🗼 В башню", callback_data="hub:back:tower")]]
    return InlineKeyboardMarkup(inline_keyboard=[*kb.inline_keyboard, *extra])
