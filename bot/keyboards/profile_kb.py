"""Клавиатура профиля: передышка, этаж, меню, титулы, полные характеристики."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t


def profile_view_keyboard(*, locale: str = "ru") -> InlineKeyboardMarkup:
    """Только нужные кнопки (без полного хаба башни)."""
    loc = locale if locale in ("ru", "en") else "ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛏️ Передышка (1 мин)", callback_data="prf:rest")],
            [
                InlineKeyboardButton(text=t(loc, "menu_floor"), callback_data="mnu:flr"),
                InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub"),
                InlineKeyboardButton(text=t(loc, "menu_titles"), callback_data="mnu:ttl"),
            ],
            [InlineKeyboardButton(text="📊 Полные характеристики", callback_data="prf:full")],
        ],
    )


def profile_full_stats_keyboard(*, locale: str = "ru") -> InlineKeyboardMarkup:
    """Экран полных характеристик: назад + те же переходы."""
    loc = locale if locale in ("ru", "en") else "ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(loc, "profile_back_compact"), callback_data="prf:back")],
            [InlineKeyboardButton(text="🛏️ Передышка (1 мин)", callback_data="prf:rest")],
            [
                InlineKeyboardButton(text=t(loc, "menu_floor"), callback_data="mnu:flr"),
                InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub"),
                InlineKeyboardButton(text=t(loc, "menu_titles"), callback_data="mnu:ttl"),
            ],
        ],
    )
