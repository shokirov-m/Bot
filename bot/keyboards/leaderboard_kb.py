"""Inline-клавиатура категорий топа."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row


def leaderboard_categories_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📈 Уровень", callback_data="top:cat:lvl"),
                InlineKeyboardButton(text="🗺️ Этаж", callback_data="top:cat:flr"),
            ],
            [
                InlineKeyboardButton(text="💪 Статы", callback_data="top:cat:pow"),
                InlineKeyboardButton(text="💰 Золото", callback_data="top:cat:gld"),
            ],
            menu_nav_button_row(),
        ],
    )
