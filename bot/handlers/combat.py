"""
Callback-и боя: атака, скиллы, побег, предмет-заглушка.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.combat_states import CombatStates
from db.repository import character_repo, user_repo
from services import combat_idle_service, combat_service

router = Router(name="combat")


@router.message(Command("fixbattle"), Command("fix_battle"), Command("фиксбой"))
async def cmd_fixbattle(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Сброс застрявшего FSM боя (при наличии данных боя — поражение)."""
    try:
        if message.from_user is None:
            return
        text = await combat_service.user_fixbattle_command(
            message=message,
            session=session,
            state=state,
        )
        await message.answer(text, parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("fixbattle")
        await message.answer("Ошибка. Попробуй ещё раз или напиши админу.")


@router.callback_query(F.data.startswith("cb:"))
async def on_combat_callback(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка кнопок поля боя."""
    try:
        if query.from_user is None or query.data is None:
            await query.answer()
            return

        if await state.get_state() != CombatStates.in_battle.state:
            await query.answer("Нет активного боя. Открой /floor.", show_alert=True)
            return

        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            combat_idle_service.cancel_combat_idle_timer(int(query.from_user.id))
            await state.clear()
            return

        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            combat_idle_service.cancel_combat_idle_timer(int(query.from_user.id))
            await state.clear()
            return

        parts = query.data.split(":")
        code = parts[1] if len(parts) > 1 else ""

        action = code
        skill_index: int | None = None
        item_id: int | None = None

        if code == "sk" and len(parts) >= 3:
            action = "sk"
            try:
                skill_index = int(parts[2])
            except ValueError:
                await query.answer()
                return
        elif code == "itm" and len(parts) >= 3:
            action = "itm"
            try:
                item_id = int(parts[2])
            except ValueError:
                await query.answer()
                return

        await combat_service.handle_combat_callback(
            query=query,
            session=session,
            state=state,
            character=char,
            action=action,
            skill_index=skill_index,
            item_id=item_id,
        )
    except Exception:
        logger.exception("Ошибка в боевом callback")
        try:
            if query.from_user is not None:
                combat_idle_service.cancel_combat_idle_timer(int(query.from_user.id))
            await state.clear()
        except Exception:
            logger.debug("combat callback: state.clear после ошибки")
        try:
            await query.answer("Ошибка боя: состояние сброшено. Открой этаж заново.", show_alert=True)
        except Exception:
            pass
