"""Выбор активного титула."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from game.characters.titles import TITLE_BY_KEY


def titles_pick_keyboard(unlocked_keys: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for key in unlocked_keys:
        t = TITLE_BY_KEY.get(key)
        if t is None:
            continue
        label = f"🏆 {t.name_ru}"
        if len(label) > 42:
            label = label[:39] + "…"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"ttl:eq:{key}")],
        )
    rows.append(
        [InlineKeyboardButton(text="❌ Снять титул", callback_data="ttl:clr")],
    )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
