"""Инлайн-клавиатура админ-панели."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Сводка", callback_data="adm:stats"),
                InlineKeyboardButton(text="👤 Игрок", callback_data="adm:user"),
            ],
            [
                InlineKeyboardButton(text="💰 Выдать золото", callback_data="adm:give"),
                InlineKeyboardButton(text="📜 Логи", callback_data="adm:logs"),
            ],
            [
                InlineKeyboardButton(text="📋 Логи (все)", callback_data="adm:logs_all"),
                InlineKeyboardButton(text="🎁 Промокоды", callback_data="adm:promo"),
            ],
            [
                InlineKeyboardButton(text="🚫 Бан", callback_data="adm:ban"),
                InlineKeyboardButton(text="✅ Разбан", callback_data="adm:unban"),
            ],
            [
                InlineKeyboardButton(text="📢 Рассылка", callback_data="adm:broadcast"),
            ],
        ],
    )


def admin_promo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📃 Список", callback_data="adm:promo_list"),
                InlineKeyboardButton(text="❓ Справка add", callback_data="adm:promo_help"),
            ],
            [
                InlineKeyboardButton(text="✏️ Ввод команды promo", callback_data="adm:promo_cmd"),
            ],
            [
                InlineKeyboardButton(text="⬅️ В панель", callback_data="adm:hub"),
            ],
        ],
    )


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✖️ Отмена", callback_data="adm:cancel"),
            ],
        ],
    )


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ В панель", callback_data="adm:hub"),
            ],
        ],
    )
