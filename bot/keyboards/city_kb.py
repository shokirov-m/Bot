"""Клавиатура городского хаба (кузница, таверна, экономика, рынок)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.crafting.workshop_constants import WORKSHOP_ORDERS_HUB_FLOOR
from game.tower.progression import floor_data


def city_hub_keyboard(
    combat_floor: int,
    character: Character,
    *,
    locale: str = "ru",
) -> InlineKeyboardMarkup:
    from game.locations import hub_floors as hf

    _ = locale
    f = int(combat_floor)
    if hf.is_city_hub_floor(f):
        anchor = int(hf.city_anchor_from_hub_floor(f) or 0)
        back_cb = "hub:back:tower"
    else:
        city = floor_data.get_city_for_floor(
            f,
            highest_reached=int(character.highest_floor_reached),
        )
        anchor = int(city.after_floor) if city is not None else f
        back_cb = f"fl:{f}:return"
    if anchor == 0:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⚒️ Кузница", callback_data=f"frg:main:{anchor}")],
                [InlineKeyboardButton(text="🍺 Таверна", callback_data=f"tvr:open:{anchor}")],
                [InlineKeyboardButton(text="🏛️ Рынок", callback_data=f"cty:mkt:{anchor}:open")],
                [
                    InlineKeyboardButton(text="⚔️ Стражник", callback_data=f"cty:{anchor}:view"),
                    InlineKeyboardButton(text="📜 Писарь", callback_data=f"cty:f3npc:scribe:{anchor}"),
                ],
                [
                    InlineKeyboardButton(text="🌿 Мара", callback_data=f"cty:f3npc:herb:{anchor}"),
                ],
                [InlineKeyboardButton(text="🗺️ В башню", callback_data=back_cb)],
                menu_nav_button_row(),
            ],
        )
    hub_rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="⚒️ Кузница", callback_data=f"frg:main:{anchor}")],
    ]
    if f == WORKSHOP_ORDERS_HUB_FLOOR:
        hub_rows.append(
            [InlineKeyboardButton(text="📋 Кузница: заказы", callback_data=f"wso:open:{f}")],
        )
    hub_rows.extend(
        [
            [InlineKeyboardButton(text="🍺 Таверна", callback_data=f"tvr:open:{anchor}")],
            [InlineKeyboardButton(text="🏪 Лавка", callback_data=f"shp:main:{anchor}:c")],
            [
                InlineKeyboardButton(text="⚔️ Стражник", callback_data=f"cty:{anchor}:view"),
                InlineKeyboardButton(text="💸 Экономика", callback_data=f"ecy:hub:{anchor}"),
            ],
            [InlineKeyboardButton(text="🗺️ В башню", callback_data=back_cb)],
            menu_nav_button_row(),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=hub_rows)
