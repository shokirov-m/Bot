"""Inline-кнопки зоны «Лес Начал» (этажи 1–10): грибы, дух."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row


def forest_mushroom_keyboard(floor_number: int, slot_code: str) -> InlineKeyboardMarkup:
    fl = int(floor_number)
    sc = str(slot_code)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🍄 Съесть (+HP)",
                    callback_data=f"flf:gms:{fl}:{sc}:eat",
                ),
                InlineKeyboardButton(
                    text="☠️ Рискнуть (яд!)",
                    callback_data=f"flf:gms:{fl}:{sc}:poi",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗺️ К этажу",
                    callback_data=f"fl:{fl}:return",
                ),
            ],
            menu_nav_button_row(),
        ],
    )


def forest_spirit_keyboard(floor_number: int, slot_code: str) -> InlineKeyboardMarkup:
    fl = int(floor_number)
    sc = str(slot_code)
    row = [
        InlineKeyboardButton(text="🌫️ Тропа 1", callback_data=f"flf:spl:{fl}:{sc}:0"),
        InlineKeyboardButton(text="🍃 Тропа 2", callback_data=f"flf:spl:{fl}:{sc}:1"),
        InlineKeyboardButton(text="✨ Тропа 3", callback_data=f"flf:spl:{fl}:{sc}:2"),
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row,
            [
                InlineKeyboardButton(
                    text="🗺️ К этажу",
                    callback_data=f"fl:{fl}:return",
                ),
            ],
            menu_nav_button_row(),
        ],
    )
