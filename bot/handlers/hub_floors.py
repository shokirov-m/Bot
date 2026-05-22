"""Переходы на хаб-этажи: библиотека, города."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.hub_floor_kb import hub_travel_menu_keyboard
from bot.states.combat_states import CombatStates
from db.repository import character_repo, user_repo
from game.locations import hub_floors as hf
from game.locations.hub_floors import LIBRARY_HUB_FLOOR
from services.progression.floor_service import (
    floor_keyboard_for_character,
    format_library_hub_message,
    push_floor_screen_ui,
    travel_to_floor,
)
from utils.telegram.game_ui import push_game_ui

router = Router(name="hub_floors")


@router.callback_query(F.data == "mnu:hubs")
async def menu_hub_travel_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Сначала /start.", show_alert=True)
            return
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=(
                "🗺️ <b>Хаб-локации</b>\n\n"
                "<i>Отдельные этажи вне башни: библиотека гримуаров и города. "
                "Бои здесь не ведутся.</i>"
            ),
            reply_markup=hub_travel_menu_keyboard(char),
            target_message=callback.message,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("mnu:hubs")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hub:go:"))
async def hub_travel_go(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        target = int(callback.data.split(":")[-1])
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer()
            return
        hf.remember_tower_floor(char)
        ok, err = await travel_to_floor(
            session,
            char,
            target,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            bot=callback.bot,
        )
        if not ok:
            await callback.answer(err or "Нельзя перейти.", show_alert=True)
            return
        await session.flush()
        if hf.is_library_hub_floor(target):
            from bot.keyboards.hub_floor_kb import library_hub_screen_keyboard

            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=format_library_hub_message(char),
                reply_markup=library_hub_screen_keyboard(char),
                target_message=callback.message,
                character=char,
            )
        else:
            kb = await floor_keyboard_for_character(
                session,
                char,
                telegram_user_id=callback.from_user.id,
            )
            await push_floor_screen_ui(
                session,
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                character=char,
                reply_markup=kb,
                target_message=callback.message,
            )
        await callback.answer(
            "Библиотека" if target == LIBRARY_HUB_FLOOR else f"Этаж {char.floor_number}",
        )
    except Exception:
        logger.exception("hub:go")
        await callback.answer("Ошибка перехода.", show_alert=True)


@router.callback_query(F.data == "hub:back:tower")
async def hub_back_tower(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None or callback.from_user is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer()
            return
        dest = hf.pop_return_tower_floor(char)
        ok, err = await travel_to_floor(
            session,
            char,
            dest,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            bot=callback.bot,
        )
        if not ok:
            await callback.answer(err or "Нельзя.", show_alert=True)
            return
        await session.flush()
        kb = await floor_keyboard_for_character(
            session,
            char,
            telegram_user_id=callback.from_user.id,
        )
        await push_floor_screen_ui(
            session,
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            character=char,
            reply_markup=kb,
            target_message=callback.message,
        )
        await callback.answer(f"Башня · этаж {dest}")
    except Exception:
        logger.exception("hub:back")
        await callback.answer("Ошибка.", show_alert=True)
