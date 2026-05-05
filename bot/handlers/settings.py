"""
Настройки: смена имени за золото, промокоды, язык, ID, подсказки.
"""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, set_locale, t
from bot.keyboards.settings_kb import (
    settings_cancel_keyboard,
    settings_reset_confirm_keyboard,
    settings_screen_keyboard,
    settings_stat_reset_confirm_keyboard,
)
from bot.states.combat_states import CombatStates
from bot.states.settings_states import SettingsStates
from bot.utils.game_art import menu_settings_photo_path
from bot.utils.game_ui import push_game_ui
from config import settings
from db.repository import character_repo, user_repo
from services import anticheat_service, character_service, stat_bonus_service
from services import unlock_service
from services.referral_service import referral_bot_link, resolve_bot_username_for_referral
from services.settings_service import redeem_promo, try_paid_rename
from utils.game_images_prefs import set_game_images_hidden, game_images_enabled
from utils.ui import LINE_SEP
from bot.states.registration_states import RegistrationStates

router = Router(name="settings")


def _settings_body_html(locale: str) -> str:
    loc = locale if locale in ("ru", "en") else "ru"
    return (
        f"{t(loc, 'settings_title')}\n"
        f"{LINE_SEP}\n"
        f"{t(loc, 'settings_intro')}"
    )


def _settings_reply_kb(locale: str, char, user) -> InlineKeyboardMarkup:
    return settings_screen_keyboard(
        locale=locale,
        character=char,
        notify_golden_goblin=bool(user.notify_golden_goblin),
    )


async def _char_gate(
    session: AsyncSession,
    message: Message | CallbackQuery,
) -> tuple[object, object] | None:
    if message.from_user is None:
        return None
    user = await user_repo.get_by_telegram_id(session, message.from_user.id)
    if user is None or user.is_banned:
        return None
    char = await character_repo.get_by_user_id(session, user.id)
    if char is None:
        return None
    return user, char


@router.message(Command("settings"))
@router.message(Command("настройки"))
async def cmd_settings(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await message.answer(t("ru", "settings_combat_block"))
            return
        pair = await _char_gate(session, message)
        if pair is None:
            await message.answer("Сначала /start.")
            return
        user, char = pair
        loc = get_locale(char, message.from_user.language_code)
        await state.clear()
        await message.answer(
            _settings_body_html(loc),
            parse_mode=ParseMode.HTML,
            reply_markup=_settings_reply_kb(loc, char, user),
        )
    except Exception:
        logger.exception("cmd_settings")
        await message.answer("Ошибка.")


@router.callback_query(F.data == "mnu:stg")
async def menu_open_settings(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            loc = "ru"
            await callback.answer(t(loc, "settings_combat_block"), show_alert=True)
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Сначала /start.", show_alert=True)
            return
        user, char = pair
        if not unlock_service.is_unlocked(char, "menu_settings"):
            await callback.answer("Раздел недоступен.", show_alert=True)
            return
        loc = get_locale(char, callback.from_user.language_code)
        await state.clear()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_settings_body_html(loc),
            reply_markup=_settings_reply_kb(loc, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("mnu:stg")
        await callback.answer("Ошибка.", show_alert=True)


def _loc_from_message(message: Message, char) -> str:
    return get_locale(char, message.from_user.language_code if message.from_user else None)


@router.callback_query(F.data == "stg:rename")
async def stg_rename_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "settings_combat_block"), show_alert=True)
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        cost = int(settings.DISPLAY_NAME_CHANGE_GOLD)
        await state.set_state(SettingsStates.waiting_new_name)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"{t(loc, 'settings_title')}\n{LINE_SEP}\n{t(loc, 'settings_rename_intro', gold=cost)}",
            reply_markup=settings_cancel_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:rename")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:promo")
async def stg_promo_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "settings_combat_block"), show_alert=True)
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        await state.set_state(SettingsStates.waiting_promo)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"{t(loc, 'settings_title')}\n{LINE_SEP}\n{t(loc, 'settings_promo_prompt')}",
            reply_markup=settings_cancel_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:promo")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:stat_rst")
async def stg_stat_reset_prompt(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "settings_combat_block"), show_alert=True)
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        if not character_service.stat_alloc_reset_available_today(char):
            await callback.answer(t(loc, "settings_stat_reset_today"), show_alert=True)
            return
        pts = character_service.count_allocated_stat_points_over_nominal(char)
        if pts <= 0:
            await callback.answer(t(loc, "settings_stat_reset_none"), show_alert=True)
            return
        cost = int(character_service.STAT_ALLOC_RESET_COST_GOLD)
        if int(char.gold) < cost:
            await callback.answer(t(loc, "settings_stat_reset_no_gold", gold=cost), show_alert=True)
            return
        await state.clear()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"{t(loc, 'settings_title')}\n{LINE_SEP}\n{t(loc, 'settings_stat_reset_warn', gold=cost, points=pts)}",
            reply_markup=settings_stat_reset_confirm_keyboard(locale=loc, gold=cost),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:stat_rst")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:stat_rst:back")
async def stg_stat_reset_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await state.clear()
            await callback.answer()
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        await state.clear()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_settings_body_html(loc),
            reply_markup=_settings_reply_kb(loc, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:stat_rst:back")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:stat_rst:go")
async def stg_stat_reset_execute(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "settings_combat_block"), show_alert=True)
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        pts = character_service.count_allocated_stat_points_over_nominal(char)
        cost = int(character_service.STAT_ALLOC_RESET_COST_GOLD)
        prior_eff = await stat_bonus_service.effective_primary_stats(session, char)
        ok, err_key = character_service.try_paid_reset_stat_allocations(char)
        if not ok:
            await callback.answer(t(loc, err_key, gold=cost), show_alert=True)
            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=_settings_body_html(loc),
                reply_markup=_settings_reply_kb(loc, char, user),
                target_message=callback.message,
                photo_path=menu_settings_photo_path(),
                character=char,
            )
            return
        await character_service.refresh_hp_mp_from_effective(session, char, prior_effective_stats=prior_eff)
        await session.flush()
        await state.clear()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"{t(loc, 'settings_title')}\n{LINE_SEP}\n{t(loc, 'settings_stat_reset_done', points=pts, gold=cost)}",
            reply_markup=_settings_reply_kb(loc, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:stat_rst:go")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:refer")
async def stg_referral(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "settings_combat_block"), show_alert=True)
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        un = await resolve_bot_username_for_referral(callback.bot)
        if not un:
            await callback.answer(t(loc, "settings_referral_no_username"), show_alert=True)
            return
        link = referral_bot_link(bot_username=un, telegram_id=int(callback.from_user.id))
        safe_link = html.escape(link)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"{t(loc, 'settings_referral_title')}\n{LINE_SEP}\n{t(loc, 'settings_referral_body', link=safe_link)}",
            reply_markup=_settings_reply_kb(loc, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:refer")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:lang")
async def stg_lang_toggle(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        cur = get_locale(char, callback.from_user.language_code)
        nxt = "en" if cur == "ru" else "ru"
        set_locale(char, nxt)
        await session.commit()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_settings_body_html(nxt),
            reply_markup=_settings_reply_kb(nxt, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer(t(nxt, "settings_lang_switched", lang=nxt.upper()), show_alert=False)
    except Exception:
        logger.exception("stg:lang")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:img")
async def stg_game_images_toggle(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "settings_combat_block"), show_alert=True)
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        set_game_images_hidden(char, game_images_enabled(char))
        await session.commit()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_settings_body_html(loc),
            reply_markup=_settings_reply_kb(loc, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:img")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:gob_notif")
async def stg_golden_goblin_notify_toggle(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "settings_combat_block"), show_alert=True)
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        user.notify_golden_goblin = not bool(user.notify_golden_goblin)
        await session.commit()
        loc = get_locale(char, callback.from_user.language_code)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_settings_body_html(loc),
            reply_markup=_settings_reply_kb(loc, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:gob_notif")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:tid")
async def stg_my_id(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        tid = callback.from_user.id
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=t(loc, "settings_my_id", tid=tid),
            reply_markup=_settings_reply_kb(loc, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:tid")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:reset")
async def stg_reset_prompt(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "settings_combat_block"), show_alert=True)
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        await state.clear()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"{t(loc, 'settings_title')}\n{LINE_SEP}\n{t(loc, 'settings_reset_warn')}",
            reply_markup=settings_reset_confirm_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:reset")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:reset:back")
async def stg_reset_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await state.clear()
            await callback.answer()
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        await state.clear()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_settings_body_html(loc),
            reply_markup=_settings_reply_kb(loc, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:reset:back")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:reset:go")
async def stg_reset_execute(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "settings_combat_block"), show_alert=True)
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        await character_repo.lock_character_row(session, char.id)
        await character_service.delete_character_and_all_progress(session, char)
        await session.commit()

        # Сразу начать регистрацию заново (как /start без существующего героя).
        await state.clear()
        await state.set_state(RegistrationStates.waiting_gender)
        from bot.handlers.start import TOWER_WAKE_LORE, GENDER_PROMPT, _gender_pick_keyboard

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"{TOWER_WAKE_LORE}{GENDER_PROMPT}",
            reply_markup=_gender_pick_keyboard(),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:reset:go")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:tips")
async def stg_tips(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=t(loc, "settings_tips_body"),
            reply_markup=_settings_reply_kb(loc, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stg:tips")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stg:cancel")
async def stg_cancel(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        pair = await _char_gate(session, callback)
        if pair is None:
            await state.clear()
            await callback.answer()
            return
        user, char = pair
        loc = get_locale(char, callback.from_user.language_code)
        await state.clear()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_settings_body_html(loc),
            reply_markup=_settings_reply_kb(loc, char, user),
            target_message=callback.message,
            photo_path=menu_settings_photo_path(),
            character=char,
        )
        await callback.answer(t(loc, "settings_fsm_cancelled"))
    except Exception:
        logger.exception("stg:cancel")
        await state.clear()
        await callback.answer()


@router.message(StateFilter(SettingsStates.waiting_new_name), F.text)
async def on_new_name_text(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None or not message.text:
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await state.clear()
            return
        pair = await _char_gate(session, message)
        if pair is None:
            await state.clear()
            return
        user, char = pair
        loc = _loc_from_message(message, char)
        cost = int(settings.DISPLAY_NAME_CHANGE_GOLD)
        ok, err_key = try_paid_rename(char, message.text)
        if not ok:
            if err_key == "settings_rename_no_gold":
                await message.answer(
                    t(loc, "settings_rename_no_gold", gold=cost),
                    parse_mode=ParseMode.HTML,
                )
            elif err_key:
                await message.answer(t(loc, err_key), parse_mode=ParseMode.HTML)
            return
        await session.commit()
        await state.clear()
        nm = html.escape(char.display_name)
        await message.answer(
            t(loc, "settings_rename_done", name=nm, gold=cost),
            parse_mode=ParseMode.HTML,
            reply_markup=_settings_reply_kb(loc, char, user),
        )
    except Exception:
        logger.exception("on_new_name_text")
        await state.clear()
        await message.answer("Ошибка.")


@router.message(StateFilter(SettingsStates.waiting_promo), F.text)
async def on_promo_text(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None or not message.text:
            return
        pair = await _char_gate(session, message)
        if pair is None:
            await state.clear()
            return
        user, char = pair
        loc = _loc_from_message(message, char)
        ok, key, fmt = await redeem_promo(
            session,
            user=user,
            character=char,
            raw_code=message.text,
            bot=message.bot,
        )
        if not ok:
            await message.answer(t(loc, key), parse_mode=ParseMode.HTML)
            return

        g = int(fmt.get("gold", 0))
        if g > 0 and settings.ANTICHEAT_ENABLED:
            await anticheat_service.record_gold_gain(
                session,
                char,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                gold_delta=g,
                bot=message.bot,
            )

        await session.commit()
        await state.clear()

        rune_part = ""
        if int(fmt.get("rune", 0)) > 0:
            rune_part = t(loc, "settings_promo_rune", rune=int(fmt["rune"]))
        level_part = ""
        lv = int(fmt.get("levels", 0))
        if lv > 0:
            level_part = t(loc, "settings_promo_levels", n=lv)
        items_part = ""
        if fmt.get("item_names"):
            items_part = t(loc, "settings_promo_items", items=html.escape(str(fmt["item_names"])))
        pet_part = ""
        ps = fmt.get("pet_status")
        pnm = fmt.get("pet_name")
        if ps == "new" and pnm:
            pet_part = t(loc, "settings_promo_pet_new", name=html.escape(str(pnm)))
        elif ps == "dup" and pnm:
            pet_part = t(loc, "settings_promo_pet_dup", name=html.escape(str(pnm)))

        await message.answer(
            t(
                loc,
                "settings_promo_ok",
                gold=int(fmt.get("gold", 0)),
                xp=int(fmt.get("xp", 0)),
                rune_part=rune_part,
                level_part=level_part,
                items_part=items_part,
                pet_part=pet_part,
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=_settings_reply_kb(loc, char, user),
        )
    except Exception:
        logger.exception("on_promo_text")
        await state.clear()
        await message.answer("Ошибка.")


@router.message(StateFilter(SettingsStates.waiting_new_name))
@router.message(StateFilter(SettingsStates.waiting_promo))
async def on_settings_non_text(message: Message, state: FSMContext) -> None:
    """Игнорировать стикеры/фото в режиме ввода — мягкая подсказка."""
    await message.answer("Нужно текстовое сообщение или нажми «Отмена».")
