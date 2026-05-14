"""Клавиатура экрана «Настройки»."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from db.models.character import Character
from utils.game_images_prefs import game_images_enabled


def settings_screen_keyboard(
    *,
    locale: str,
    character: Character | None = None,
    notify_golden_goblin: bool = True,
    adult_age_declared: bool | None = None,
    adult_content_enabled: bool | None = None,
) -> InlineKeyboardMarkup:
    loc = "ru"
    hide = character is not None and not game_images_enabled(character)
    img_btn = t(loc, "settings_images_enable") if hide else t(loc, "settings_images_disable")
    _ = notify_golden_goblin  # флаг читается в подменю «Уведомления»
    if adult_age_declared is None:
        adult_btn = "🔞 18+ (подтвердить)"
    elif adult_age_declared is False:
        adult_btn = "🔞 18+ недоступно"
    else:
        adult_btn = "🔞 18+ контент: ВКЛ" if bool(adult_content_enabled) else "🔞 18+ контент: ВЫКЛ"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_rename_btn"),
                    callback_data="stg:rename",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_promo_btn"),
                    callback_data="stg:promo",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_referral_btn"),
                    callback_data="stg:refer",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_stat_reset_btn"),
                    callback_data="stg:stat_rst",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_my_id_btn"),
                    callback_data="stg:tid",
                ),
                InlineKeyboardButton(
                    text=t(loc, "settings_tips_btn"),
                    callback_data="stg:tips",
                ),
            ],
            [
                InlineKeyboardButton(text="🔔 Уведомления", callback_data="stg:notif"),
            ],
            [
                InlineKeyboardButton(text="📖 Справочник", callback_data="stg:wiki"),
            ],
            [
                InlineKeyboardButton(
                    text=img_btn,
                    callback_data="stg:img",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=adult_btn,
                    callback_data="stg:adult",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_reset_btn"),
                    callback_data="stg:reset",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_back_menu"),
                    callback_data="mnu:hub",
                ),
            ],
        ],
    )


def settings_stat_reset_confirm_keyboard(*, locale: str, gold: int) -> InlineKeyboardMarkup:
    loc = "ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_stat_reset_yes", gold=gold),
                    callback_data="stg:stat_rst:go",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_stat_reset_no"),
                    callback_data="stg:stat_rst:back",
                ),
            ],
        ],
    )


def settings_reset_confirm_keyboard(*, locale: str) -> InlineKeyboardMarkup:
    loc = "ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_reset_yes"),
                    callback_data="stg:reset:go",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_reset_no"),
                    callback_data="stg:reset:back",
                ),
            ],
        ],
    )


def settings_cancel_keyboard(*, locale: str) -> InlineKeyboardMarkup:
    loc = "ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(loc, "settings_cancel_btn"),
                    callback_data="stg:cancel",
                ),
            ],
        ],
    )


def settings_notifications_hub_keyboard(*, locale: str, notify_golden_goblin: bool) -> InlineKeyboardMarkup:
    loc = "ru"
    goblin_btn = (
        t(loc, "settings_golden_goblin_notify_disable")
        if notify_golden_goblin
        else t(loc, "settings_golden_goblin_notify_enable")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=goblin_btn, callback_data="stg:gob_notif"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="stg:root"),
            ],
        ],
    )


def settings_handbook_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="stg:root")]],
    )
