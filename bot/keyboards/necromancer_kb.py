"""Клавиатуры некроманта: меню, ритуал, ковчег."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.locations.hub_floors import LIBRARY_HUB_FLOOR
from game.necromancer.service import (
    NECROMANCER_COST_GOLD,
    SKELETON_ROLES,
    can_purchase_necromancer,
    get_party_skeleton_keys,
    is_necromancer,
    unlocked_skeleton_keys,
)


def necromancer_menu_keyboard(character: Character) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if is_necromancer(character):
        rows.append(
            [InlineKeyboardButton(text="⚰️ Ковчег костей", callback_data="prf:necro:coffin")],
        )
        from game.locations import grimoire_library as lib

        if lib.library_unlocked(character):
            rows.append(
                [
                    InlineKeyboardButton(
                        text="📖 Высшие гримуары",
                        callback_data=f"lib:prestige:{LIBRARY_HUB_FLOOR}",
                    ),
                ],
            )
    else:
        can_ok, _ = can_purchase_necromancer(character)
        if can_ok or int(character.level) >= 60:
            rows.append(
                [InlineKeyboardButton(text="💀 Ритуал класса", callback_data="prf:necro:ritual")],
            )
    rows.append([InlineKeyboardButton(text="◀️ Специализация", callback_data="prf:spec")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
    rows.append([InlineKeyboardButton(text="◀️ Некромант", callback_data="prf:necro:menu")])
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
    rows.append([InlineKeyboardButton(text="◀️ Некромант", callback_data="prf:necro:menu")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def necromancer_spec_extra_row(character: Character) -> list[InlineKeyboardButton] | None:
    if int(character.level) < 60:
        return None
    return [
        InlineKeyboardButton(text="💀 Некромант", callback_data="prf:necro:menu"),
    ]
