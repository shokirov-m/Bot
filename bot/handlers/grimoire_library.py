"""Библиотека гримуаров — хаб-этаж 9001."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

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
from db.models.character import Character
from db.repository import character_repo, user_repo
from game.archetypes.grimoires import SKILL_GRIMOIRES
from game.locations import grimoire_library as lib
from game.locations.hub_floors import LIBRARY_HUB_FLOOR
import services.progression.grimoire_library_service as library_service
from services.progression.floor_service import format_library_hub_message, travel_to_floor
from utils.telegram.game_ui import push_game_ui

if TYPE_CHECKING:
    from aiogram.types import User

router = Router(name="grimoire_library")


async def _load_char(session: AsyncSession, telegram_id: int) -> tuple[object | None, Character | None]:
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None, None
    char = await character_repo.get_by_user_id(session, user.id)
    return user, char


async def _library_guard(
    session: AsyncSession,
    state: FSMContext,
    query: CallbackQuery,
    *,
    ensure_on_hub: bool = True,
) -> Character | None:
    """Персонаж, не в бою, библиотека открыта; опционально — на этаже 9001."""
    if query.from_user is None:
        return None
    if await state.get_state() == CombatStates.in_battle.state:
        await query.answer("Сначала заверши бой.", show_alert=True)
        return None
    _, char = await _load_char(session, query.from_user.id)
    if char is None:
        await query.answer("Нет персонажа.", show_alert=True)
        return None
    if not lib.library_unlocked(char):
        await query.answer("Библиотека откроется после 18-го яруса.", show_alert=True)
        return None
    if ensure_on_hub and not lib.library_floor_ok(char, LIBRARY_HUB_FLOOR):
        await query.answer("Открой библиотеку с этажа 9001 или из меню «Локации».", show_alert=True)
        return None
    return char


@router.callback_query(F.data.regexp(r"^lib:open:(\d+)$"))
async def on_library_open(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.data is None or query.message is None or query.bot is None:
            await query.answer()
            return
        from game.locations import hub_floors as hf

        _, char = await _load_char(session, query.from_user.id if query.from_user else 0)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        if not lib.library_unlocked(char):
            await query.answer("Библиотека откроется после 18-го яруса.", show_alert=True)
            return
        if int(char.floor_number) != LIBRARY_HUB_FLOOR:
            hf.remember_tower_floor(char)
            ok, err = await travel_to_floor(
                session,
                char,
                LIBRARY_HUB_FLOOR,
                telegram_id=query.from_user.id if query.from_user else None,
                username=query.from_user.username if query.from_user else None,
                bot=query.bot,
            )
            if not ok:
                await query.answer(err or "Нельзя перейти.", show_alert=True)
                return
        char = await _library_guard(session, state, query)
        if char is None:
            return
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=format_library_hub_message(char),
            reply_markup=library_hub_keyboard(char, LIBRARY_HUB_FLOOR),
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
        if query.data is None or query.message is None or query.bot is None:
            await query.answer()
            return
        m = re.match(r"^lib:cls:([a-z]+):(\d+)$", query.data)
        if m is None:
            await query.answer()
            return
        arch = m.group(1)
        from game.locations import hub_floors as hf

        _, char = await _load_char(session, query.from_user.id if query.from_user else 0)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        if not lib.library_unlocked(char):
            await query.answer("Библиотека откроется после 18-го яруса.", show_alert=True)
            return
        if int(char.floor_number) != LIBRARY_HUB_FLOOR:
            hf.remember_tower_floor(char)
            ok, err = await travel_to_floor(
                session,
                char,
                LIBRARY_HUB_FLOOR,
                telegram_id=query.from_user.id if query.from_user else None,
                username=query.from_user.username if query.from_user else None,
                bot=query.bot,
            )
            if not ok:
                await query.answer(err or "Нельзя перейти.", show_alert=True)
                return
        char = await _library_guard(session, state, query)
        if char is None:
            return
        if arch not in lib.library_archetype_keys_for(char):
            await query.answer("Нет такого раздела.", show_alert=True)
            return
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=library_service.format_class_catalog_html(char, arch),
            reply_markup=library_class_keyboard(char, arch, LIBRARY_HUB_FLOOR),
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
        if query.data is None or query.message is None or query.bot is None:
            await query.answer()
            return
        m = re.match(r"^lib:view:([a-z0-9_]+):(\d+)$", query.data)
        if m is None:
            await query.answer()
            return
        gkey = m.group(1)
        char = await _library_guard(session, state, query)
        if char is None:
            return
        if gkey not in SKILL_GRIMOIRES:
            await query.answer("Книга не найдена.", show_alert=True)
            return
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=library_service.format_offer_detail_html(char, gkey),
            reply_markup=library_offer_keyboard(char, gkey, LIBRARY_HUB_FLOOR),
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
        if query.data is None or query.message is None or query.bot is None:
            await query.answer()
            return
        m = re.match(r"^lib:buy:([a-z0-9_]+):(\d+)$", query.data)
        if m is None:
            await query.answer()
            return
        gkey = m.group(1)
        char = await _library_guard(session, state, query)
        if char is None:
            return
        await character_repo.lock_character_row(session, char.id)
        ok, msg = await library_service.try_purchase(
            session,
            char,
            gkey,
            require_library_hub=True,
        )
        await session.commit()
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        await query.answer("Куплено!", show_alert=False)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=library_service.format_offer_detail_html(char, gkey) + f"\n\n✅ {msg}",
            reply_markup=library_offer_keyboard(char, gkey, LIBRARY_HUB_FLOOR),
            target_message=query.message,
            character=char,
        )
    except Exception:
        logger.exception("lib:buy")
        await query.answer("Ошибка покупки.", show_alert=True)
