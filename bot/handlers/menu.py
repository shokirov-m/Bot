"""
Главное меню: колбэки mnu:* вместо /profile, /floor, /inv (титулы — /titles и статус).
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.inventory import _bag_intro
from bot.handlers.auction import _auction_intro_html, _clear_auction_fsm_only
from bot.handlers.leaderboard import INTRO_HTML as TOP_INTRO_HTML
from bot.handlers.profile import build_profile_html_async, clamp_profile_caption_for_photo
from bot.handlers.titles import _screen_html as titles_screen_html
from bot.keyboards.leaderboard_kb import leaderboard_categories_keyboard
from bot.keyboards.inventory_kb import bag_tab_keyboard
from bot.keyboards.auction_kb import auction_hub_keyboard
from bot.keyboards.daily_kb import daily_screen_keyboard
from bot.keyboards.menu_kb import main_menu_keyboard
from bot.keyboards.profile_kb import profile_view_keyboard
from bot.keyboards.title_kb import titles_pick_keyboard
from bot.states.combat_states import CombatStates
from bot.i18n import get_locale, t
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, inventory_repo, user_repo
from bot.handlers.quests import render_quests_hub
from services import daily_service, title_service
from services.daily_screen_service import build_daily_body_html
from services.floor_service import floor_keyboard_for_character, push_floor_screen_ui
from services.menu_hub_service import format_menu_hub_html
from services.rest_service import apply_completed_rest_if_needed
from utils.game_images_prefs import game_images_enabled
from utils.profile_portraits import portrait_path_for_character

router = Router(name="menu")

async def _edit_same_message(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    """Одно якорное сообщение: с этажа (фото) и с текста — через push_game_ui."""
    if callback.message is None or callback.bot is None:
        return
    await push_game_ui(
        state,
        callback.bot,
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=reply_markup,
        target_message=callback.message,
        photo_path=None,
    )


async def _char_or_alert(
    session: AsyncSession,
    query: CallbackQuery,
) -> tuple[object | None, object | None]:
    if query.from_user is None:
        await query.answer()
        return None, None
    user = await user_repo.get_by_telegram_id(session, query.from_user.id)
    if user is None or user.is_banned:
        await query.answer("Нет доступа.", show_alert=True)
        return None, None
    char = await character_repo.get_by_user_id(session, user.id)
    if char is None:
        await query.answer("Сначала создай героя через /start.", show_alert=True)
        return None, None
    return user, char


@router.callback_query(F.data == "mnu:hub")
async def menu_hub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Сначала /start.", show_alert=True)
            return
        if callback.message is None:
            await callback.answer()
            return
        loc = get_locale(char, callback.from_user.language_code)
        from game.characters.global_passives import refresh_global_passives

        refresh_global_passives(char)
        await session.flush()
        hub_text = format_menu_hub_html(char, locale=loc)
        await _edit_same_message(callback, state, hub_text, main_menu_keyboard(locale=loc))
        await callback.answer()
    except Exception:
        logger.exception("mnu:hub")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "mnu:qst")
async def menu_quests(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        text, kb = await render_quests_hub(session, char)
        await _edit_same_message(callback, state, text, kb)
        await callback.answer()
    except Exception:
        logger.exception("mnu:qst")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "mnu:dly")
async def menu_daily(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        loc = get_locale(char, callback.from_user.language_code)
        body, sub = await build_daily_body_html(
            callback.bot,
            callback.from_user.id,
            char,
            locale=loc,
            title_html=t(loc, "daily_header"),
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=daily_screen_keyboard(
                subscribed=sub,
                can_claim=daily_service.can_claim_daily_today(char) if sub else False,
                locale=loc,
            ),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("mnu:dly")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "mnu:prf")
async def menu_profile(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        title_service.refresh_unlocks(char)
        apply_completed_rest_if_needed(char)
        await session.flush()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        text = await build_profile_html_async(session, char)
        p = portrait_path_for_character(char) if game_images_enabled(char) else None
        cap = clamp_profile_caption_for_photo(text) if p is not None else text
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=cap,
            reply_markup=profile_view_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=p,
        )
        await callback.answer()
    except Exception:
        logger.exception("mnu:prf")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "mnu:flr")
async def menu_floor(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        kb = await floor_keyboard_for_character(session, char)
        await push_floor_screen_ui(
            session,
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            character=char,
            reply_markup=kb,
            target_message=callback.message,
        )
        await callback.answer()
    except Exception:
        logger.exception("mnu:flr")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "mnu:inv")
async def menu_inventory(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        bag = await inventory_repo.list_bag_items(session, char.id)
        text = _bag_intro(len(bag))
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=bag_tab_keyboard(bag, 0),
            target_message=callback.message,
        )
        await callback.answer()
    except Exception:
        logger.exception("mnu:inv")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "mnu:top")
async def menu_top(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None:
            await callback.answer()
            return
        await _edit_same_message(callback, state, TOP_INTRO_HTML, leaderboard_categories_keyboard())
        await callback.answer()
    except Exception:
        logger.exception("mnu:top")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "mnu:auc")
async def menu_auction(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None:
            await callback.answer()
            return
        await _clear_auction_fsm_only(state)
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        await _edit_same_message(
            callback,
            state,
            _auction_intro_html(),
            auction_hub_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("mnu:auc")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "mnu:ttl")
async def menu_titles(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        text = titles_screen_html(char)
        keys = title_service.unlocked_sorted(char)
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        kb = titles_pick_keyboard(keys) if keys else main_menu_keyboard(locale=loc)
        await _edit_same_message(callback, state, text, kb)
        await callback.answer()
    except Exception:
        logger.exception("mnu:ttl")
        await callback.answer("Ошибка.", show_alert=True)
