"""Клавиатуры PvE Колизея (колбэк col:)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from game.coliseum.coliseum_data import COLISEUM_FIGHTERS


def coliseum_main_keyboard(
    *,
    next_id: int | None,
    page: int,
    can_fight: bool,
) -> InlineKeyboardMarkup:
    """Меню: правила, список по странице, бой."""
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(
        [InlineKeyboardButton(text="📜 Правила", callback_data="col:rules")],
    )
    # 10 бойцов на страницу, 5 страниц
    per_page = 10
    pages = 5
    p = max(0, min(int(page), pages - 1))
    start = p * per_page + 1
    for i in range(start, min(start + per_page, 51)):
        f = COLISEUM_FIGHTERS[i - 1]
        label = f"{i:02d}. {f.name[:18]}"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"col:info:{i}")],
        )
    nav: list[InlineKeyboardButton] = []
    if p > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"col:pg:{p - 1}"))
    nav.append(InlineKeyboardButton(text=f"{p + 1}/{pages}", callback_data="col:noop"))
    if p < pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"col:pg:{p + 1}"))
    if nav:
        rows.append(nav)
    if can_fight and next_id is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"⚔️ Следующий: #{next_id}",
                    callback_data=f"col:fight:{next_id}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="mnu:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def coliseum_fight_confirm_keyboard(fighter_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ В бой", callback_data=f"col:go:{fighter_id}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="col:menu"),
            ],
        ],
    )
