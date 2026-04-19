"""Клавиатуры экрана «Дом»."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character


def home_main_keyboard(character: Character, *, locale: str = "ru") -> InlineKeyboardMarkup:
    """Гардероб и передышка всегда; верстак и алхимия по уровню дома."""
    from services import home_service
    from services.rest_service import apply_completed_rest_if_needed, rest_seconds_left

    loc = locale if locale in ("ru", "en") else "ru"
    apply_completed_rest_if_needed(character)
    sec = rest_seconds_left(character)
    rest_txt = t(loc, "profile_rest_btn_wait", sec=sec) if sec > 0 else t(loc, "profile_rest_btn_start")

    rows: list[list[InlineKeyboardButton]] = []

    rows.append([InlineKeyboardButton(text="🪞 Гардероб", callback_data="hom:ward")])
    rows.append([InlineKeyboardButton(text=rest_txt[:64], callback_data="hom:rest")])

    cost = home_service.next_home_upgrade_cost(character)
    if cost is not None:
        hl = home_service.home_level(character)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🏡 Улучшить дом ({cost} 💰) · ур.{hl}→{hl + 1}"[:64],
                    callback_data="hom:lvup",
                ),
            ],
        )

    if home_service.can_access_workbench(character):
        rows.append([InlineKeyboardButton(text="🛠 Верстак", callback_data="hom:bench")])
    if home_service.can_access_alchemy(character):
        rows.append([InlineKeyboardButton(text="⚗️ Алхимия", callback_data="hom:alch")])

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wardrobe_keyboard(portrait_keys: list[str], *, current_key: str) -> InlineKeyboardMarkup:
    """Два действия на облик: превью картинки и выбор."""
    from utils.profile_portraits import portrait_label_ru

    rows: list[list[InlineKeyboardButton]] = []
    for pk in portrait_keys:
        ru = portrait_label_ru(pk)
        preview_lbl = (ru[:16] + "…") if len(ru) > 17 else ru
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"👁 {preview_lbl}"[:36],
                    callback_data=f"hom:pv:{pk}"[:64],
                ),
                InlineKeyboardButton(
                    text=("✓ Надет" if pk == current_key else "✅ Выбрать"),
                    callback_data=f"hom:setp:{pk}"[:64],
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workbench_keyboard(*, can_upgrade: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_upgrade:
        rows.append(
            [InlineKeyboardButton(text="⬆ Улучшить верстак", callback_data="hom:wb:up")],
        )
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def alchemy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")],
            menu_nav_button_row(),
        ],
    )


def wardrobe_preview_keyboard(portrait_key: str, *, is_current: bool) -> InlineKeyboardMarkup:
    pk = portrait_key[:48]
    rows: list[list[InlineKeyboardButton]] = []
    if not is_current:
        rows.append(
            [InlineKeyboardButton(text="✅ Надеть этот облик", callback_data=f"hom:setp:{pk}"[:64])],
        )
    rows.append([InlineKeyboardButton(text="📋 К списку обликов", callback_data="hom:ward")])
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
