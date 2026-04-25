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
from services.combat_fsm_backup import (
    clear_combat_backup,
    combat_backup_failure_reason,
    try_restore_combat_backup,
)
from utils.debug_agent_log import log_debug

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
        has_combat = bool(st_data.get("combat"))
        combat_top_keys: list[str] = []
        c0 = st_data.get("combat")
        if isinstance(c0, dict):
            combat_top_keys = [str(k) for k in list(c0.keys())[:12]]
        # #region agent log
        log_debug(
            "combat.py:on_combat_callback:entry",
            "combat cb",
            {
                "state_is_in_battle": raw_state == CombatStates.in_battle.state,
                "raw_state_str": str(raw_state),
                "has_combat": has_combat,
                "combat_top_keys": combat_top_keys,
                "st_data_key_count": len(st_data),
                "data_keys": [str(k) for k in st_data.keys()][:20],
            },
            hypothesis_id="H1_H2_H4",
        )
        # #endregion
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
                has_combat = bool(st_data.get("combat"))
                # #region agent log
                log_debug(
                    "combat.py:on_combat_callback:meta_recover",
                    "restored combat from meta backup",
                    {"rec_keys": [str(k) for k in list((rec or {}).keys())[:12]]},
                    hypothesis_id="H2_H3",
                    run_id="post-fix",
                )
                # #endregion
            else:
                # #region agent log
                log_debug(
                    "combat.py:on_combat_callback:meta_recover_fail",
                    "FSM/backup gap: restore from meta not possible",
                    {
                        "fail_reason": combat_backup_failure_reason(char),
                        "state_is_in_battle": raw_state == CombatStates.in_battle.state,
                        "had_st_data_combat": bool(st_data.get("combat")),
                    },
                    hypothesis_id="H2_H3_H5",
                )
                # #endregion

        if raw_state != CombatStates.in_battle.state:
            if st_data.get("combat"):
                # #region agent log
                log_debug(
                    "combat.py:on_combat_callback:restore",
                    "restoring in_battle from combat payload",
                    {"combat_key_count": len(combat_top_keys)},
                    hypothesis_id="H1",
                )
                # #endregion
                await state.set_state(CombatStates.in_battle)
            else:
                # #region agent log
                log_debug(
                    "combat.py:on_combat_callback:no_fight",
                    "reject: not in_battle and no combat",
                    {},
                    hypothesis_id="H2_H3",
                )
                # #endregion
                await query.answer("Нет активного боя. Открой /floor.", show_alert=True)
                return
        else:
            if not st_data.get("combat"):
                # #region agent log
                log_debug(
                    "combat.py:on_combat_callback:stale",
                    "in_battle but combat missing -> clear",
                    {},
                    hypothesis_id="H4",
                )
                # #endregion
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
    except Exception as e:
        logger.exception("Ошибка в боевом callback")
        # #region agent log
        log_debug(
            "combat.py:on_combat_callback:exception",
            "unhandled in combat cb",
            {"exc_type": type(e).__name__, "exc_msg": (str(e) or "")[:220]},
            hypothesis_id="H6",
        )
        # #endregion
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
