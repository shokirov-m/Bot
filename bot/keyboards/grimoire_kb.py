"""Клавиатуры гримуаров и цепочки наставника."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.archetypes.grimoires import (
    SKILL_GRIMOIRES,
    SUPREME_GRIMOIRES,
    inventory_keys,
    learned_keys,
    supreme_keys_for_parent,
)
from game.archetypes import manager as arch_manager
import services.progression.class_mentor_quest_service as mentor_quest_mod


def grimoires_menu_keyboard(character: Character) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    inv = inventory_keys(character)
    for gk in inv[:8]:
        g = SKILL_GRIMOIRES.get(gk) or SUPREME_GRIMOIRES.get(gk)
        if g:
            label = getattr(g, "name_ru", gk)[:28]
        else:
            label = gk[:28]
        rows.append(
            [InlineKeyboardButton(text=f"📖 {label}", callback_data=f"grim:read:{gk}")],
        )
    if len(inv) > 8:
        rows.append(
            [InlineKeyboardButton(text=f"… ещё {len(inv) - 8}", callback_data="grim:list")],
        )
    rows.append([InlineKeyboardButton(text="📚 Все изученные", callback_data="grim:learned")])
    rows.append([InlineKeyboardButton(text="◀️ Специализация", callback_data="prf:spec")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def grimoires_inventory_list_keyboard(character: Character, offset: int = 8) -> InlineKeyboardMarkup:
    """Страница сумки гримуаров (после первых 8 в меню)."""
    inv = inventory_keys(character)
    page_size = 8
    off = max(8, int(offset))
    rows: list[list[InlineKeyboardButton]] = []
    for gk in inv[off : off + page_size]:
        g = SKILL_GRIMOIRES.get(gk) or SUPREME_GRIMOIRES.get(gk)
        label = getattr(g, "name_ru", gk)[:28] if g else gk[:28]
        rows.append(
            [InlineKeyboardButton(text=f"📖 {label}", callback_data=f"grim:read:{gk}")],
        )
    nav: list[InlineKeyboardButton] = []
    if off > 8:
        prev_off = max(8, off - page_size)
        nav.append(
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"grim:list:{prev_off}"),
        )
    if off + page_size < len(inv):
        nav.append(
            InlineKeyboardButton(text="▶️ Ещё", callback_data=f"grim:list:{off + page_size}"),
        )
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="◀️ Гримуары", callback_data="prf:grimoires")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def grimoires_learned_keyboard(character: Character) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    learned = sorted(learned_keys(character))
    for gk in learned:
        sg = SUPREME_GRIMOIRES.get(gk)
        if sg is None:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{sg.emoji} {sg.name_ru[:26]}",
                    callback_data=f"grim:supreme:{gk}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="◀️ Гримуары", callback_data="prf:grimoires")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def grimoire_read_confirm_keyboard(grimoire_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Прочитать",
                    callback_data=f"grim:confirm:{grimoire_key}",
                ),
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="prf:grimoires")],
        ],
    )


def supreme_use_confirm_keyboard(grimoire_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ Сменить класс",
                    callback_data=f"grim:supreme:{grimoire_key}",
                ),
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="prf:grimoires")],
        ],
    )


def mentor_quest_keyboard(character: Character) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    pk = mentor_quest_mod.parent_class_key(character)
    if mentor_quest_mod.can_pick_reward(character) and pk:
        for sk in supreme_keys_for_parent(pk):
            sg = SUPREME_GRIMOIRES.get(sk)
            if sg:
                rows.append(
                    [
                        InlineKeyboardButton(
                            text=f"{sg.emoji} {sg.name_ru[:24]}",
                            callback_data=f"mentor:pick:{sk}",
                        ),
                    ],
                )
    rows.append([InlineKeyboardButton(text="📖 Мои гримуары", callback_data="prf:grimoires")])
    rows.append([InlineKeyboardButton(text="◀️ Специализация", callback_data="prf:spec")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
