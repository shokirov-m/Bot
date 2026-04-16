"""Клавиатура диалога со странником (квест)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row


def quest_back_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ К этажу",
                    callback_data=f"qst:{floor_number}:back",
                ),
            ],
            menu_nav_button_row(),
        ],
    )


def quest_dialog_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять квест",
                    callback_data=f"qst:{floor_number}:acc",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="◀️ К этажу",
                    callback_data=f"qst:{floor_number}:back",
                ),
            ],
            menu_nav_button_row(),
        ],
    )
