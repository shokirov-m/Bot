"""Клавиатура ежедневки (подписка на канал)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from bot.keyboards.menu_kb import menu_nav_button_row
from services.subscription_service import channel_public_url


def daily_screen_keyboard(*, subscribed: bool, can_claim: bool, locale: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    ch_label = t(locale, "channel_display_name")
    if not subscribed:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(locale, "daily_btn_channel", channel=ch_label),
                    url=channel_public_url(),
                ),
            ],
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(locale, "daily_btn_verify"),
                    callback_data="daily:verify",
                ),
            ],
        )
    elif can_claim:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(locale, "daily_btn_claim"),
                    callback_data="daily:claim",
                ),
            ],
        )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
