"""Выбор активного титула (два слота)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from services import title_service

TITLE_KEYS_PAGE_SIZE = 5


def titles_pick_keyboard(character: Character, unlocked_keys: list[str], *, page: int = 0) -> InlineKeyboardMarkup:
    n = len(unlocked_keys)
    pages = max(1, (n + TITLE_KEYS_PAGE_SIZE - 1) // TITLE_KEYS_PAGE_SIZE) if n else 1
    page = max(0, min(page, pages - 1))
    chunk = unlocked_keys[page * TITLE_KEYS_PAGE_SIZE : (page + 1) * TITLE_KEYS_PAGE_SIZE]

    rows: list[list[InlineKeyboardButton]] = []
    for key in chunk:
        t = title_service.title_def_for(character, key)
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
    if pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"tit:pg:{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="tit:noop"))
        if page < pages - 1:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"tit:pg:{page + 1}"))
        rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(text="❌ Снять ①", callback_data="ttl:clr1"),
            InlineKeyboardButton(text="❌ Снять ②", callback_data="ttl:clr2"),
        ],
    )
    rows.append([InlineKeyboardButton(text="❌ Снять оба", callback_data="ttl:clra")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
