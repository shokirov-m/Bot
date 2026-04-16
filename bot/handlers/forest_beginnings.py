"""Callbacks flf:* — привал, ядовитые грибы, лесной дух (этажи 1–10)."""

from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.combat_states import CombatStates
from db.repository import character_repo, user_repo
from game.floors import forest_beginnings as fb
from services import anticheat_service, character_service
from services.floor_service import floor_keyboard_for_character, push_floor_screen_ui
from utils.ui import LINE_SEP

router = Router(name="forest_beginnings")

_CAMP = re.compile(r"^flf:camp:(\d+)$")
_GMS = re.compile(r"^flf:gms:(\d+):([a-z0-9]+):(eat|poi)$")
_SPL = re.compile(r"^flf:spl:(\d+):([a-z0-9]+):([0-2])$")


@router.callback_query(F.data.regexp(r"^flf:camp:(\d+)$"))
async def on_forest_camp(
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
        m = _CAMP.match(query.data)
        if m is None:
            await query.answer()
            return
        fl = int(m.group(1))
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        if fl != int(char.floor_number):
            await query.answer("Этаж устарел.", show_alert=True)
            return
        if not fb.is_forest_beginnings_zone(fl):
            await query.answer("Привал только в лесу 1–10.", show_alert=True)
            return
        if fb.camp_used(char):
            await query.answer("Привал уже использован на этом проходе зоны.", show_alert=True)
            return
        fb.set_camp_used(char)
        char.hp_current = int(char.hp_max)
        char.mp_current = int(char.mp_max)
        await session.flush()
        suffix = (
            f"\n{LINE_SEP}\n"
            "🏕️ <b>Привал:</b> полное восстановление <b>HP</b> и <b>MP</b> "
            "<i>без траты стамины</i> (один раз, пока не поднимешься выше 10)."
        )
        await push_floor_screen_ui(
            session,
            state,
            query.bot,
            chat_id=query.message.chat.id,
            character=char,
            reply_markup=await floor_keyboard_for_character(session, char),
            target_message=query.message,
            text_suffix=suffix,
        )
        await query.answer("Отдохнул.")
    except Exception:
        logger.exception("flf:camp")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^flf:gms:(\d+):([a-z0-9]+):(eat|poi)$"))
async def on_forest_mushroom(
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
        m = _GMS.match(query.data)
        if m is None:
            await query.answer()
            return
        fl, slot, act = int(m.group(1)), m.group(2), m.group(3)
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        if fl != int(char.floor_number):
            await query.answer("Этаж устарел.", show_alert=True)
            return
        if not fb.is_forest_beginnings_zone(fl):
            await query.answer()
            return
        mx = int(char.hp_max)
        cur = int(char.hp_current)
        if act == "eat":
            heal = 10 + fl + max(0, (mx - cur) // 12)
            nh = min(mx, cur + heal)
            char.hp_current = nh
            note = f"🍄 Съел гриб: <b>+{nh - cur} HP</b>."
        else:
            dmg = 6 + fl // 2
            char.hp_current = max(1, cur - dmg)
            note = f"☠️ Яд обжёг: <b>−{dmg} HP</b>."
        await session.flush()
        suffix = f"\n{LINE_SEP}\n{note}"
        await push_floor_screen_ui(
            session,
            state,
            query.bot,
            chat_id=query.message.chat.id,
            character=char,
            reply_markup=await floor_keyboard_for_character(session, char),
            target_message=query.message,
            text_suffix=suffix,
        )
        await query.answer()
    except Exception:
        logger.exception("flf:gms")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^flf:spl:(\d+):([a-z0-9]+):([0-2])$"))
async def on_forest_spirit_choice(
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
        m = _SPL.match(query.data)
        if m is None:
            await query.answer()
            return
        fl, slot, pick_s = int(m.group(1)), m.group(2), m.group(3)
        pick = int(pick_s)
        data = await state.get_data()
        ctx = data.get("svc_forest_spirit")
        if not isinstance(ctx, dict):
            await query.answer("Выбор устарел. Открой этаж снова.", show_alert=True)
            return
        if int(ctx.get("floor", -1)) != fl or str(ctx.get("slot", "")) != slot:
            await query.answer("Выбор устарел.", show_alert=True)
            return
        correct = int(ctx.get("correct", 0))
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        if fl != int(char.floor_number):
            await query.answer("Этаж устарел.", show_alert=True)
            return
        line, dg, dhp, dmp = fb.spirit_outcome_for_choice(pick, correct)

        if dg:
            character_service.add_gold(char, dg)
            await anticheat_service.record_gold_gain(
                session,
                char,
                telegram_id=query.from_user.id,
                username=query.from_user.username,
                gold_delta=dg,
                bot=query.bot,
            )
        char.hp_current = max(1, min(int(char.hp_max), int(char.hp_current) + dhp))
        char.mp_current = max(0, min(int(char.mp_max), int(char.mp_current) + dmp))
        fb.set_spirit_used(char)
        await state.update_data(svc_forest_spirit=None)
        await session.flush()
        gold_bit = f" 💰 <b>+{dg}</b>" if dg else ""
        hp_bit = f" ❤️ <b>{dhp:+d}</b> HP" if dhp else ""
        mp_bit = f" 💧 <b>{dmp:+d}</b> MP" if dmp else ""
        suffix = (
            f"\n{LINE_SEP}\n"
            f"🦊 <b>Лесной дух</b>\n{line}"
            f"{gold_bit}{hp_bit}{mp_bit}"
        )
        await push_floor_screen_ui(
            session,
            state,
            query.bot,
            chat_id=query.message.chat.id,
            character=char,
            reply_markup=await floor_keyboard_for_character(session, char),
            target_message=query.message,
            text_suffix=suffix,
        )
        await query.answer()
    except Exception:
        logger.exception("flf:spl")
        await query.answer("Ошибка.", show_alert=True)
