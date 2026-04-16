"""Город (хаб) и кузница: inline-кнопки."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.city_kb import city_hub_keyboard
from bot.keyboards.menu_kb import menu_nav_button_row

__all__ = [
    "city_hub_keyboard",
    "forge_actions_keyboard",
    "forge_enchant_slots_keyboard",
    "forge_rune_bag_pick_keyboard",
    "forge_rune_menu_keyboard",
    "forge_rune_socket_pick_keyboard",
]


def forge_rune_menu_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Вставить руну", callback_data=f"frg:rsl:{floor_number}")],
            [InlineKeyboardButton(text="🔓 Извлечь руну", callback_data=f"frg:rrm:{floor_number}")],
            [
                InlineKeyboardButton(
                    text="⚗️ Две I → II (авто)",
                    callback_data=f"frg:rca:{floor_number}",
                ),
            ],
            [InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")],
            menu_nav_button_row(),
        ],
    )


def forge_rune_bag_pick_keyboard(
    floor_number: int,
    items: list[tuple[int, str]],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item_id, label in items[:14]:
        short = label if len(label) <= 36 else label[:33] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=short,
                    callback_data=f"frg:rsi:{floor_number}:{item_id}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"frg:rnm:{floor_number}")],
    )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def forge_rune_socket_pick_keyboard(
    floor_number: int,
    labels: list[tuple[int, str]],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, label in labels[:8]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=label[:40],
                    callback_data=f"frg:rrx:{floor_number}:{idx}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"frg:rnm:{floor_number}")],
    )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def forge_enchant_slots_keyboard(
    floor_number: int,
    slots: list[tuple[str, str]],
    *,
    ward: bool = False,
) -> InlineKeyboardMarkup:
    prefix = "enchw" if ward else "ench"
    rows: list[list[InlineKeyboardButton]] = []
    for slot_code, label in slots[:12]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=label[:64],
                    callback_data=f"frg:{prefix}:{floor_number}:{slot_code}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def forge_actions_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Заточить предмет", callback_data=f"frg:ench:{floor_number}")],
            [
                InlineKeyboardButton(
                    text="⚗️ Заточка + руна (без −1)",
                    callback_data=f"frg:enchw:{floor_number}",
                ),
            ],
            [InlineKeyboardButton(text="💎 Руны на оружии", callback_data=f"frg:rnm:{floor_number}")],
            [InlineKeyboardButton(text="🧪 Сварить настой (HP)", callback_data=f"frg:brew:{floor_number}")],
            [InlineKeyboardButton(text="⬅ В город", callback_data=f"frg:city:{floor_number}")],
            menu_nav_button_row(),
        ],
    )
