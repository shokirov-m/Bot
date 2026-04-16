"""Выбор активного титула (два слота)."""

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
        base = t.name_ru
        if len(base) > 16:
            base = base[:13] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"① {base}",
                    callback_data=f"ttl:1:{key}",
                ),
                InlineKeyboardButton(
                    text=f"② {base}",
                    callback_data=f"ttl:2:{key}",
                ),
            ],
        )
    rows.append(
        [
            InlineKeyboardButton(text="❌ Снять ①", callback_data="ttl:clr1"),
            InlineKeyboardButton(text="❌ Снять ②", callback_data="ttl:clr2"),
        ],
    )
    rows.append([InlineKeyboardButton(text="❌ Снять оба", callback_data="ttl:clra")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
