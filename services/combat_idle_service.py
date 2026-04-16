"""
Таймер бездействия в бою: 40 с без хода игрока — автоматическое поражение (как обычный слив).
Отмена при каждом действии игрока или при завершении боя.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.types import Chat, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.combat_states import CombatStates
from db.repository import character_repo, user_repo

COMBAT_IDLE_SECONDS = 40

_tasks: dict[int, asyncio.Task] = {}


def cancel_combat_idle_timer(telegram_user_id: int) -> None:
    t = _tasks.pop(int(telegram_user_id), None)
    if t is not None and not t.done():
        t.cancel()


async def arm_combat_idle_after_player_turn(
    *,
    bot: Bot,
    state: FSMContext,
    telegram_user_id: int,
) -> None:
    """
    Сбросить предыдущий таймер и запустить новый отсчёт 40 с до авто-поражения.
    Вызывать, когда у игрока снова экран хода (после ответа монстра / меню предметов).
    """
    cancel_combat_idle_timer(telegram_user_id)
    key = state.key
    if key is None:
        return
    data = await state.get_data()
    gen = int(data.get("combat_idle_gen", 0)) + 1
    await state.update_data(combat_idle_gen=gen)
    task = asyncio.create_task(
        _idle_timeout_job(
            bot=bot,
            storage=state.storage,
            key=key,
            expected_generation=gen,
            telegram_user_id=int(telegram_user_id),
        ),
        name=f"combat_idle_{telegram_user_id}",
    )
    _tasks[int(telegram_user_id)] = task


def _chat_type_for_id(chat_id: int) -> str:
    return "private" if int(chat_id) > 0 else "supergroup"


async def _idle_timeout_job(
    *,
    bot: Bot,
    storage: BaseStorage,
    key: StorageKey,
    expected_generation: int,
    telegram_user_id: int,
) -> None:
    try:
        await asyncio.sleep(COMBAT_IDLE_SECONDS)
        data = await storage.get_data(key)
        if int(data.get("combat_idle_gen", 0)) != int(expected_generation):
            return
        st = await storage.get_state(key)
        if st != CombatStates.in_battle.state:
            return
        combat_state = data.get("combat")
        if not isinstance(combat_state, dict):
            await storage.set_state(key, state=None)
            await storage.set_data(key, data={})
            return

        from db.database import get_session_factory
        from services import combat_service

        factory = get_session_factory()
        async with factory() as session:
            try:
                user = await user_repo.get_by_telegram_id(session, telegram_user_id)
                if user is None or user.is_banned:
                    await storage.set_state(key, state=None)
                    await storage.set_data(key, data={})
                    return
                char = await character_repo.get_by_user_id(session, user.id)
                if char is None:
                    await storage.set_state(key, state=None)
                    await storage.set_data(key, data={})
                    return

                mid = data.get("combat_message_id")
                cid = data.get("combat_chat_id")
                if mid is None or cid is None:
                    await storage.set_state(key, state=None)
                    await storage.set_data(key, data={})
                    return

                edit_msg = Message(
                    message_id=int(mid),
                    chat=Chat(id=int(cid), type=_chat_type_for_id(int(cid))),
                    date=datetime.now(UTC),
                    bot=bot,
                )
                ctx = FSMContext(storage=storage, key=key)
                await combat_service.defeat_from_afk_or_stuck(
                    message=edit_msg,
                    state=ctx,
                    session=session,
                    character=char,
                    combat_state=combat_state,
                    banner_html="⏱ <b>40 секунд без хода.</b> Бой засчитан как <b>поражение</b>.",
                )
                await session.commit()
            except Exception:
                logger.exception("combat idle timeout job")
                await session.rollback()
    except asyncio.CancelledError:
        raise
    finally:
        _tasks.pop(int(telegram_user_id), None)
