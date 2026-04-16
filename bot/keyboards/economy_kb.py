"""Золотые sinks в городском хабе (колбэки ecy:*)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row


def economy_hub_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    f = int(floor_number)
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🎰 Лотерея", callback_data=f"ecy:lot:{f}")],
        [
            InlineKeyboardButton(text="💰 Займ", callback_data=f"ecy:mlb:{f}"),
            InlineKeyboardButton(text="📉 Платёж", callback_data=f"ecy:mlr:{f}"),
        ],
        [InlineKeyboardButton(text="🏦 Сейф банка", callback_data=f"ecy:sfv:{f}")],
        [InlineKeyboardButton(text="🛒 Магазин (инфо)", callback_data=f"ecy:auc:{f}")],
        [InlineKeyboardButton(text="⬅ В город", callback_data=f"ecy:back:{f}")],
        menu_nav_button_row(),
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def bank_safe_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    f = int(floor_number)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ 100", callback_data=f"ecy:sfd:{f}:100"),
                InlineKeyboardButton(text="➕ 500", callback_data=f"ecy:sfd:{f}:500"),
            ],
            [
                InlineKeyboardButton(text="➖ 100", callback_data=f"ecy:sfw:{f}:100"),
                InlineKeyboardButton(text="➖ 500", callback_data=f"ecy:sfw:{f}:500"),
            ],
            [InlineKeyboardButton(text="➕ Всё влезет", callback_data=f"ecy:sfd:{f}:0")],
            [InlineKeyboardButton(text="➖ Снять всё", callback_data=f"ecy:sfw:{f}:0")],
            [InlineKeyboardButton(text="⬆️ Улучшить хранилище", callback_data=f"ecy:sfu:{f}")],
            [InlineKeyboardButton(text="⬅ Экономика", callback_data=f"ecy:hub:{f}")],
            menu_nav_button_row(),
        ],
    )
