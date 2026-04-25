"""Клавиатура профиля: меню, специализация (титулы/профессии/навыки), полные характеристики."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.characters import pets as pets_mod


def profile_spec_submenu_keyboard(character: Character, *, locale: str = "ru") -> InlineKeyboardMarkup:
    """Подменю «Специализация»: титулы, архетипы, навыки."""
    loc = locale if locale in ("ru", "en") else "ru"
    rows = [
        [InlineKeyboardButton(text=t(loc, "menu_titles"), callback_data="mnu:ttl")],
    ]
    
    # If wanderer and lvl 10+, show Archetype Selection
    if str(character.class_key or "wanderer").lower() == "wanderer" and character.level >= 10:
        rows.append([InlineKeyboardButton(text="🌟 Выбрать путь", callback_data="prf:arch_pick")])
    elif character.level >= 30:
         # Placeholder for Tier 2
         pass

    rows.extend([
        [InlineKeyboardButton(text="🌳 Древо навыков", callback_data="prf:skills")],
        [InlineKeyboardButton(text="⚔️ Экипировать навыки", callback_data="prf:skills_equip")],
        [InlineKeyboardButton(text=t(loc, "profile_back_compact"), callback_data="prf:back")],
        menu_nav_button_row(),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_view_keyboard(character: Character | None = None, *, locale: str = "ru") -> InlineKeyboardMarkup:
    """Компактный статус (передышка — в разделе «Дом»)."""
    loc = locale if locale in ("ru", "en") else "ru"
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub"),
            InlineKeyboardButton(text=t(loc, "profile_spec_btn"), callback_data="prf:spec"),
        ],
        [
            InlineKeyboardButton(text="🏆 Достижения", callback_data="prf:achievements"),
            InlineKeyboardButton(text="📊 Полные характеристики", callback_data="prf:full"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_full_stats_keyboard(*, locale: str = "ru") -> InlineKeyboardMarkup:
    """Экран полных характеристик."""
    loc = locale if locale in ("ru", "en") else "ru"
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=t(loc, "profile_back_compact"), callback_data="prf:back")],
        [
            InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub"),
            InlineKeyboardButton(text=t(loc, "profile_spec_btn"), callback_data="prf:spec"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_pet_picker_keyboard(owned: list[str], *, locale: str, active_key: str | None) -> InlineKeyboardMarkup:
    """По одному ряду на питомца + назад + меню."""
    loc = locale if locale in ("ru", "en") else "ru"
    rows: list[list[InlineKeyboardButton]] = []
    for k in owned:
        cap = pets_mod.pet_choice_button_caption(k, locale=loc, is_active=(k == active_key))
        rows.append([InlineKeyboardButton(text=cap, callback_data=f"prf:petpick:{k}")])
    rows.append([InlineKeyboardButton(text=t(loc, "profile_pet_pick_back"), callback_data="prf:petback")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
