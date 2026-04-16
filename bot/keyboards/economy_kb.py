"""Золотые sinks в городском хабе (колбэки ecy:*)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from game.economy import sinks as sink_rules


def economy_hub_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    f = int(floor_number)
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🎰 Лотерея", callback_data=f"ecy:lot:{f}")],
        [
            InlineKeyboardButton(text="💰 Займ", callback_data=f"ecy:mlb:{f}"),
            InlineKeyboardButton(text="📉 Платёж", callback_data=f"ecy:mlr:{f}"),
        ],
        [
            InlineKeyboardButton(
                text=f"🕯️ Пожертв. {sink_rules.TITHE_TIERS_GOLD[0]} 💰",
                callback_data=f"ecy:tit:{f}:0",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"🕯️ Пожертв. {sink_rules.TITHE_TIERS_GOLD[1]} 💰",
                callback_data=f"ecy:tit:{f}:1",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"🕯️ Пожертв. {sink_rules.TITHE_TIERS_GOLD[2]} 💰",
                callback_data=f"ecy:tit:{f}:2",
            ),
        ],
        [InlineKeyboardButton(text="🏦 Опека сейфа", callback_data=f"ecy:bnk:{f}")],
        [InlineKeyboardButton(text="🏛️ Аукцион (инфо)", callback_data=f"ecy:auc:{f}")],
        [InlineKeyboardButton(text="⬅ В город", callback_data=f"ecy:back:{f}")],
        menu_nav_button_row(),
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
