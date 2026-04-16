"""
Выбор базового класса (11 яр., с 10 ур.) и подкласса (57): arc:b:*, arc:s:*.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db.repository import character_repo, user_repo
from game.characters.class_arcs import (
    can_pick_base_class_on_current_floor,
    offered_base_class_keys,
    subclass_keys_for_character,
)
from services import class_arc_service
from services.floor_service import floor_keyboard_for_character, format_floor_message

router = Router(name="class_arc")


@router.callback_query(F.data.startswith("arc:b:"))
async def on_pick_base_class(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.from_user is None or query.message is None or query.data is None:
            await query.answer()
            return
        key = query.data.split(":")[-1]
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет героя.", show_alert=True)
            return
        if not can_pick_base_class_on_current_floor(char):
            await query.answer(
                "Базовый путь выбирается только на 11 этаже у наставника Эрида.",
                show_alert=True,
            )
            return
        if key not in offered_base_class_keys(char):
            await query.answer("Этот класс тебе сейчас недоступен.", show_alert=True)
            return
        await character_repo.lock_character_row(session, char.id)
        if not class_arc_service.apply_base_class(char, key):
            await query.answer("Ошибка класса.", show_alert=True)
            return
        await session.flush()
        await query.message.edit_text(
            format_floor_message(char),
            reply_markup=await floor_keyboard_for_character(session, char),
        )
        await query.answer("Путь выбран!")
    except Exception:
        logger.exception("arc:b")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("arc:s:"))
async def on_pick_subclass(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.from_user is None or query.message is None or query.data is None:
            await query.answer()
            return
        sk = query.data.split(":")[-1]
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет героя.", show_alert=True)
            return
        if sk not in subclass_keys_for_character(char):
            await query.answer("Подкласс недоступен.", show_alert=True)
            return
        if not class_arc_service.apply_subclass(char, sk):
            await query.answer("Не удалось применить подкласс.", show_alert=True)
            return
        await session.flush()
        await query.message.edit_text(
            format_floor_message(char),
            reply_markup=await floor_keyboard_for_character(session, char),
        )
        await query.answer("Углубление принято — статы ×2!")
    except Exception:
        logger.exception("arc:s")
        await query.answer("Ошибка.", show_alert=True)
