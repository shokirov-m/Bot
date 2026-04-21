"""Клавиатуры экрана «Дом» (5 уровней)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character


def home_main_keyboard(character: Character, *, locale: str = "ru") -> InlineKeyboardMarkup:
    from services import home_service
    from services.rest_service import apply_completed_rest_if_needed, rest_seconds_left

    loc = locale if locale in ("ru", "en") else "ru"
    apply_completed_rest_if_needed(character)
    sec = rest_seconds_left(character)
    rest_txt = t(loc, "profile_rest_btn_wait", sec=sec) if sec > 0 else t(loc, "profile_rest_btn_start")

    rows: list[list[InlineKeyboardButton]] = []

    # Гардероб всегда
    rows.append([InlineKeyboardButton(text="🪞 Гардероб", callback_data="hom:ward")])
    # Передышка всегда
    rows.append([InlineKeyboardButton(text=rest_txt[:64], callback_data="hom:rest")])

    # Кнопка улучшения дома
    hl = home_service.home_level(character)
    cost_gold = home_service.next_home_upgrade_cost(character)
    cost_trophy = home_service.next_home_trophy_cost(character)
    if cost_gold is not None:
        trophy_part = f" + {cost_trophy}🏆" if cost_trophy > 0 else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🏡 Улучшить дом ({cost_gold:,}💰{trophy_part}) ур.{hl}→{hl+1}"[:64],
                    callback_data="hom:lvup",
                ),
            ],
        )

    # Библиотека (ур.4+)
    if home_service.can_access_library(character):
        h_left = home_service.library_hours_until_ready(character)
        lib_label = "🔬 Библиотека (+1 стат)" if h_left == 0 else f"🔬 Библиотека (~{int(h_left)}ч)"
        rows.append([InlineKeyboardButton(text=lib_label[:64], callback_data="hom:lib")])

    # Верстак (ур.2+)
    if home_service.can_access_workbench(character):
        rows.append([InlineKeyboardButton(text="🛠 Верстак", callback_data="hom:bench")])

    # Алхимия (ур.3+)
    if home_service.can_access_alchemy(character):
        rows.append([InlineKeyboardButton(text="⚗️ Алхимия", callback_data="hom:alch")])

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def library_keyboard(*, ready: bool) -> InlineKeyboardMarkup:
    """Меню библиотеки: выбор стата (если готова) или только «назад»."""
    rows: list[list[InlineKeyboardButton]] = []
    if ready:
        rows.append([
            InlineKeyboardButton(text="⚔️ Сила", callback_data="hom:lib:str"),
            InlineKeyboardButton(text="🏹 Ловкость", callback_data="hom:lib:dex"),
        ])
        rows.append([
            InlineKeyboardButton(text="🔮 Интеллект", callback_data="hom:lib:int"),
            InlineKeyboardButton(text="❤️ Тело", callback_data="hom:lib:vit"),
        ])
        rows.append([
            InlineKeyboardButton(text="🍀 Удача", callback_data="hom:lib:luck"),
        ])
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wardrobe_keyboard(portrait_keys: list[str], *, current_key: str) -> InlineKeyboardMarkup:
    from utils.profile_portraits import portrait_label_ru

    rows: list[list[InlineKeyboardButton]] = []
    for pk in portrait_keys:
        ru = portrait_label_ru(pk)
        prefix = "✓ " if pk == current_key else ""
        label = f"{prefix}{ru}"
        if len(label) > 36:
            label = label[:33] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"hom:pv:{pk}"[:64],
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
    if is_current:
        rows.append([InlineKeyboardButton(text="✓ Надет", callback_data="hom:pvcur")])
    else:
        rows.append([InlineKeyboardButton(text="✅ Надеть", callback_data=f"hom:setp:{pk}"[:64])])
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data="hom:ward")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
