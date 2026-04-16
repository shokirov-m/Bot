"""
Городской хаб с этажа (callback fl:{n}:city).
Вынесено из floor.py, чтобы маршрут был явным блоком перед бетой.
"""

from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, t
from bot.keyboards.city_kb import city_hub_keyboard
from bot.states.combat_states import CombatStates
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, user_repo
from game.characters import pets as pets_mod
from game.floors import floor_data
from services.floor_service import format_city_hub_message

router = Router(name="city")


@router.callback_query(F.data.regexp(r"^fl:(\d+):city$"))
async def on_city_hub_open(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши текущий бой.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        parts = query.data.split(":")
        floor = int(parts[1])
        if floor != char.floor_number:
            await query.answer("Этаж устарел. Открой /floor снова.", show_alert=True)
            return
        if floor_data.get_city_for_floor(char.floor_number) is None:
            await query.answer()
            return
        loc = get_locale(char, query.from_user.language_code)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=format_city_hub_message(char),
            reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
            target_message=query.message,
        )
        await query.answer()
    except Exception:
        logger.exception("city hub")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "mnu:cty")
async def menu_open_city_from_hub(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Город из главного меню (только если текущий этаж — городской хаб)."""
    try:
        if query.from_user is None or query.message is None:
            await query.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши текущий бой.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        loc = get_locale(char, query.from_user.language_code)
        if floor_data.get_city_for_floor(char.floor_number) is None:
            await query.answer(t(loc, "menu_city_unavailable"), show_alert=True)
            return
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=format_city_hub_message(char),
            reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
            target_message=query.message,
        )
        await query.answer()
    except Exception:
        logger.exception("mnu:cty")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cty:pet:(1|3):(\d+)$"))
async def on_city_pet_summon(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши текущий бой.", show_alert=True)
            return
        m = re.match(r"^cty:pet:(1|3):(\d+)$", query.data)
        if m is None:
            await query.answer()
            return
        pulls = int(m.group(1))
        floor_key = int(m.group(2))
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        loc = get_locale(char, query.from_user.language_code)
        if floor_key != char.floor_number or floor_data.get_city_for_floor(char.floor_number) is None:
            await query.answer(t(loc, "menu_city_unavailable"), show_alert=True)
            return
        ok, msg = pets_mod.try_city_pet_summon(char, pulls=pulls)
        await session.flush()
        plain = re.sub(r"<[^>]+>", "", msg)
        if ok:
            await query.answer(plain[:180] if plain else "Ок.", show_alert=False)
        else:
            await query.answer(plain[:200] if plain else "Нельзя.", show_alert=True)
        suffix = f"\n\n{msg}" if msg else ""
        await query.message.edit_text(
            format_city_hub_message(char) + suffix,
            reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("cty:pet")
        await query.answer("Ошибка.", show_alert=True)
