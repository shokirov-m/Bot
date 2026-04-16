"""
Городской хаб с этажа (callback fl:{n}:city).
Вынесено из floor.py, чтобы маршрут был явным блоком перед бетой.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.city_kb import city_hub_keyboard
from bot.states.combat_states import CombatStates
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, user_repo
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
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=format_city_hub_message(char),
            reply_markup=city_hub_keyboard(char.floor_number),
            target_message=query.message,
        )
        await query.answer()
    except Exception:
        logger.exception("city hub")
        await query.answer("Ошибка.", show_alert=True)
