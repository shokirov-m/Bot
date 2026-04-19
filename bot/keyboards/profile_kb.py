"""Клавиатура профиля: передышка, меню, специализация (титулы/профессии/навыки), полные характеристики."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.characters import pets as pets_mod
from services.rest_service import apply_completed_rest_if_needed, rest_seconds_left


def _rest_button_caption(character: Character | None, *, locale: str) -> str:
    loc = locale if locale in ("ru", "en") else "ru"
    if character is None:
        return t(loc, "profile_rest_btn_start")
    apply_completed_rest_if_needed(character)
    sec = rest_seconds_left(character)
    if sec > 0:
        return t(loc, "profile_rest_btn_wait", sec=sec)
    return t(loc, "profile_rest_btn_start")


def profile_spec_submenu_keyboard(*, locale: str = "ru") -> InlineKeyboardMarkup:
    """Подменю «Специализация»: титулы, профессии, навыки."""
    loc = locale if locale in ("ru", "en") else "ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(loc, "menu_titles"), callback_data="mnu:ttl")],
            [InlineKeyboardButton(text=t(loc, "menu_professions"), callback_data="mnu:prof")],
            [InlineKeyboardButton(text=t(loc, "profile_skills_btn"), callback_data="prf:skills")],
            [InlineKeyboardButton(text=t(loc, "profile_back_compact"), callback_data="prf:back")],
            menu_nav_button_row(),
        ],
    )


def profile_view_keyboard(character: Character | None = None, *, locale: str = "ru") -> InlineKeyboardMarkup:
    """Компактный статус: передышка, навигация."""
    loc = locale if locale in ("ru", "en") else "ru"
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=_rest_button_caption(character, locale=loc), callback_data="prf:rest")],
        [
            InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub"),
            InlineKeyboardButton(text=t(loc, "profile_spec_btn"), callback_data="prf:spec"),
        ],
        [InlineKeyboardButton(text="📊 Полные характеристики", callback_data="prf:full")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_full_stats_keyboard(*, locale: str = "ru") -> InlineKeyboardMarkup:
    """Экран полных характеристик: без передышки (она в статусе)."""
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
