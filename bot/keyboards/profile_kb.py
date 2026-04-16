"""Клавиатура профиля: передышка, этаж, меню, титулы, питомец, полные характеристики."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from db.models.character import Character
from game.characters import pets as pets_mod


def profile_view_keyboard(character: Character | None = None, *, locale: str = "ru") -> InlineKeyboardMarkup:
    """Компактный статус: передышка как на экране полных характеристик."""
    loc = locale if locale in ("ru", "en") else "ru"
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🛏️ Передышка (1 мин)", callback_data="prf:rest")],
        [
            InlineKeyboardButton(text=t(loc, "menu_floor"), callback_data="mnu:flr"),
            InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub"),
            InlineKeyboardButton(text=t(loc, "menu_titles"), callback_data="mnu:ttl"),
        ],
        [InlineKeyboardButton(text="📊 Полные характеристики", callback_data="prf:full")],
    ]
    if character is not None and pets_mod.owned_keys(character):
        rows.append(
            [InlineKeyboardButton(text="🐾 Питомец", callback_data="prf:pet")],
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
