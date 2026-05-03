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
from services.combat_fsm_backup import clear_combat_backup, try_restore_combat_backup
from utils.combat_crash_dump import write_crash_dump

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

        # FSM и Redis/Memory иногда сбрасываются, а сообщение с кнопками остаётся — см. meta-бэкап.
        st_data = await state.get_data()
        raw_state = await state.get_state()
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

        await session.refresh(char)

        if (raw_state != CombatStates.in_battle.state) or (not st_data.get("combat")):
            rec = try_restore_combat_backup(char)
            if rec is not None:
                await state.set_state(CombatStates.in_battle)
                await state.update_data(combat=rec)
                st_data = await state.get_data()
                raw_state = await state.get_state()

        if raw_state != CombatStates.in_battle.state:
            if st_data.get("combat"):
                await state.set_state(CombatStates.in_battle)
            else:
                await query.answer("Нет активного боя. Открой /floor.", show_alert=True)
                return
        else:
            if not st_data.get("combat"):
                clear_combat_backup(char)
                try:
                    await session.flush()
                except Exception:
                    pass
                await state.clear()
                combat_idle_service.cancel_combat_idle_timer(int(query.from_user.id))
                await query.answer("Сессия боя устарела. Открой /floor.", show_alert=True)
                return

        parts = query.data.split(":")
        code = parts[1] if len(parts) > 1 else ""

        # Информационная кнопка (пассивка в бою) — просто закрыть тост
        if code == "noop":
            await query.answer()
            return

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
        elif code == "run":
            if len(parts) >= 3 and parts[2] == "yes":
                action = "run"
            else:
                action = "run_ask"

        await combat_service.handle_combat_callback(
            query=query,
            session=session,
            state=state,
            character=char,
            action=action,
            skill_index=skill_index,
            item_id=item_id,
        )
    except Exception as exc:
        # Полный лог нужен для диагностики; пользователю даём короткое сообщение с типом ошибки
        # и НЕ обнуляем FSM/бэкап — бой можно продолжать кликом по той же кнопке.
        logger.exception(
            "Сбой в боевом callback (action={}, skill_index={}, item_id={}): {}",
            action if 'action' in locals() else '?',
            skill_index if 'skill_index' in locals() else None,
            item_id if 'item_id' in locals() else None,
            type(exc).__name__,
        )
        try:
            data_dump = await state.get_data()
            combat_dump = data_dump.get("combat") if isinstance(data_dump, dict) else None
            user_id = int(query.from_user.id) if query.from_user is not None else None
            char_id = int(char.id) if 'char' in locals() and char is not None else None
            write_crash_dump(
                exc=exc,
                action=action if 'action' in locals() else None,
                skill_index=skill_index if 'skill_index' in locals() else None,
                item_id=item_id if 'item_id' in locals() else None,
                user_id=user_id,
                character_id=char_id,
                combat_state=combat_dump if isinstance(combat_dump, dict) else None,
            )
        except Exception:
            logger.debug("combat crash: запись дампа не удалась")
        try:
            await query.answer(
                f"Сбой при действии ({type(exc).__name__}). "
                "Попробуй ещё раз или используй /fixbattle.",
                show_alert=True,
            )
        except Exception:
            pass
