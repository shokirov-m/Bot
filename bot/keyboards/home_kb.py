"""Клавиатуры экрана «Дом»."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row


def home_main_keyboard(*, floor_number: int) -> InlineKeyboardMarkup:
    fl = int(floor_number)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👗 Гардероб", callback_data="hom:ward")],
            [InlineKeyboardButton(text="🛠 Верстак", callback_data="hom:bench")],
            [InlineKeyboardButton(text="⚗️ Алхимия", callback_data="hom:alch")],
            [
                InlineKeyboardButton(
                    text="🏪 Магазин",
                    callback_data=f"shp:main:{fl}:h",
                ),
            ],
            menu_nav_button_row(),
        ],
    )


def wardrobe_keyboard(portrait_keys: list[str], *, current_key: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, pk in enumerate(portrait_keys):
        label = pk[:26] + "…" if len(pk) > 26 else pk
        prefix = "✓ " if pk == current_key else ""
        row.append(
            InlineKeyboardButton(
                text=f"{prefix}{label}"[:36],
                callback_data=f"hom:setp:{pk}"[:64],
            ),
        )
        if len(row) >= 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workbench_keyboard(*, can_upgrade: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_upgrade:
        rows.append(
            [InlineKeyboardButton(text="⬆ Улучшить верстак", callback_data="hom:wb:up")],
        )
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def alchemy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")],
            menu_nav_button_row(),
        ],
    )
