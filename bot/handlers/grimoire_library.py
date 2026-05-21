"""Библиотека гримуаров между 18↔19 ярусами."""

from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.grimoire_library_kb import (
    library_class_keyboard,
    library_hub_keyboard,
    library_offer_keyboard,
)
from bot.states.combat_states import CombatStates
from db.repository import character_repo, user_repo
from game.archetypes.grimoires import SKILL_GRIMOIRES
from game.locations import grimoire_library as lib
import services.progression.grimoire_library_service as library_service
from utils.telegram.game_ui import push_game_ui

router = Router(name="grimoire_library")


async def _load_char(session: AsyncSession, telegram_id: int):
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None, None
    char = await character_repo.get_by_user_id(session, user.id)
    return user, char


@router.callback_query(F.data.regexp(r"^lib:open:(\d+)$"))
async def on_library_open(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        floor = int(query.data.split(":")[2])
        _, char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if not lib.library_floor_ok(char, floor):
            await query.answer("Библиотека недоступна на этом ярусе.", show_alert=True)
            return
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=library_service.format_library_hub_html(char),
            reply_markup=library_hub_keyboard(floor),
            target_message=query.message,
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("lib:open")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^lib:cls:([a-z]+):(\d+)$"))
async def on_library_class(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        m = re.match(r"^lib:cls:([a-z]+):(\d+)$", query.data)
        if m is None:
            await query.answer()
            return
        arch, floor = m.group(1), int(m.group(2))
        if arch not in lib.LIBRARY_ARCHETYPES:
            await query.answer("Нет такого раздела.", show_alert=True)
            return
        _, char = await _load_char(session, query.from_user.id)
        if char is None or not lib.library_floor_ok(char, floor):
            await query.answer("Библиотека недоступна.", show_alert=True)
            return
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=library_service.format_class_catalog_html(char, arch),
            reply_markup=library_class_keyboard(char, arch, floor),
            target_message=query.message,
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("lib:cls")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^lib:view:([a-z0-9_]+):(\d+)$"))
async def on_library_view(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        m = re.match(r"^lib:view:([a-z0-9_]+):(\d+)$", query.data)
        if m is None:
            await query.answer()
            return
        gkey, floor = m.group(1), int(m.group(2))
        _, char = await _load_char(session, query.from_user.id)
        if char is None or not lib.library_floor_ok(char, floor):
            await query.answer("Библиотека недоступна.", show_alert=True)
            return
        if gkey not in SKILL_GRIMOIRES:
            await query.answer("Книга не найдена.", show_alert=True)
            return
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=library_service.format_offer_detail_html(char, gkey),
            reply_markup=library_offer_keyboard(char, gkey, floor),
            target_message=query.message,
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("lib:view")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^lib:buy:([a-z0-9_]+):(\d+)$"))
async def on_library_buy(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        m = re.match(r"^lib:buy:([a-z0-9_]+):(\d+)$", query.data)
        if m is None:
            await query.answer()
            return
        gkey, floor = m.group(1), int(m.group(2))
        _, char = await _load_char(session, query.from_user.id)
        if char is None or not lib.library_floor_ok(char, floor):
            await query.answer("Библиотека недоступна.", show_alert=True)
            return
        await character_repo.lock_character_row(session, char.id)
        ok, msg = await library_service.try_purchase(session, char, gkey)
        await session.commit()
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        g = SKILL_GRIMOIRES[gkey]
        await query.answer("Куплено!", show_alert=False)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=library_service.format_offer_detail_html(char, gkey) + f"\n\n✅ {msg}",
            reply_markup=library_offer_keyboard(char, gkey, floor),
            target_message=query.message,
            character=char,
        )
    except Exception:
        logger.exception("lib:buy")
        await query.answer("Ошибка покупки.", show_alert=True)
