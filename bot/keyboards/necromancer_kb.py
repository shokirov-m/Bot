"""Клавиатуры некроманта: ритуал и ковчег костей."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.necromancer.service import (
    NECROMANCER_COST_GOLD,
    SKELETON_ROLES,
    get_party_skeleton_keys,
    is_necromancer,
    unlocked_skeleton_keys,
)


def necromancer_ritual_keyboard(*, can_buy: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_buy:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"💀 Ритуал ({NECROMANCER_COST_GOLD // 1000}k 💰)",
                    callback_data="prf:necro:buy",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="prf:spec")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def necromancer_coffin_keyboard(character: Character) -> InlineKeyboardMarkup:
    party = set(get_party_skeleton_keys(character))
    unlocked = unlocked_skeleton_keys(character)
    rows: list[list[InlineKeyboardButton]] = []
    for key, rd in SKELETON_ROLES.items():
        if key not in unlocked:
            continue
        mark = "✅" if key in party else "⬜"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {rd.emoji} {rd.name_ru}",
                    callback_data=f"prf:necro:tog:{key}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="◀️ Специализация", callback_data="prf:spec")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def necromancer_spec_extra_row(character: Character) -> list[InlineKeyboardButton] | None:
    if is_necromancer(character):
        return [
            InlineKeyboardButton(text="⚰️ Ковчег костей", callback_data="prf:necro:coffin"),
        ]
    if int(character.level) >= 60:
        return [
            InlineKeyboardButton(text="💀 Ритуал некроманта", callback_data="prf:necro"),
        ]
    return None
