"""Экран выбора профессий (два слота) — по образцу титулов."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from bot.keyboards.menu_kb import menu_nav_button_row
from services import profession_service as ps

PROF_PAGE_SIZE = 6


def professions_pick_keyboard(keys: list[str], *, page: int = 0, locale: str = "ru") -> InlineKeyboardMarkup:
    loc = locale if locale in ("ru", "en") else "ru"
    n = len(keys)
    pages = max(1, (n + PROF_PAGE_SIZE - 1) // PROF_PAGE_SIZE) if n else 1
    page = max(0, min(page, pages - 1))
    chunk = keys[page * PROF_PAGE_SIZE : (page + 1) * PROF_PAGE_SIZE]

    rows: list[list[InlineKeyboardButton]] = []

    for key in chunk:
        base = ps.profession_display_name(key, locale=loc)
        if len(base) > 14:
            base = base[:11] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"① {base}",
                    callback_data=f"prn:1:{key}",
                ),
                InlineKeyboardButton(
                    text=f"② {base}",
                    callback_data=f"prn:2:{key}",
                ),
            ],
        )
    if pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"prn:pg:{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="prn:noop"))
        if page < pages - 1:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"prn:pg:{page + 1}"))
        rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(text=t(loc, "professions_clear_slot1"), callback_data="prn:clr1"),
            InlineKeyboardButton(text=t(loc, "professions_clear_slot2"), callback_data="prn:clr2"),
        ],
    )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
