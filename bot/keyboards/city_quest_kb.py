"""Диалог поручения стражи в городе."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row


def city_quest_offer_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять поручение",
                    callback_data=f"cty:{floor_number}:acc",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="◀️ В город",
                    callback_data=f"cty:{floor_number}:hub",
                ),
            ],
            menu_nav_button_row(),
        ],
    )


def city_quest_hub_only_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ В город",
                    callback_data=f"cty:{floor_number}:hub",
                ),
            ],
            menu_nav_button_row(),
        ],
    )
