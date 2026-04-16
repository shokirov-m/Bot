"""Кнопки онбординга после создания героя."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def tutorial_hints_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗺️ Что такое этаж?", callback_data="tut:tip:flr")],
            [InlineKeyboardButton(text="🎒 Про инвентарь", callback_data="tut:tip:inv")],
        ],
    )
