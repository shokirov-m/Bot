"""Callbacks flf:* — привал, ядовитые грибы, лесной дух (этажи 1–10)."""

from __future__ import annotations

import html
import random
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.combat_states import CombatStates
from db.repository import character_repo, inventory_repo, user_repo
from game.floors import forest_beginnings as fb
from game.floors import rotten_swamps as rs
from game.floors.monsters import build_spawns_for_floor
from game.items import loot as loot_tables
from services import anticheat_service, character_service
from services.floor_service import floor_keyboard_for_character, push_floor_screen_ui
from utils.ui import LINE_SEP

router = Router(name="forest_beginnings")

_CAMP = re.compile(r"^flf:camp:(\d+)$")
_GMS = re.compile(r"^flf:gms:(\d+):([a-z0-9]+):(eat|skip)$")
_SPL = re.compile(r"^flf:spl:(\d+):([a-z0-9]+):([0-2])$")


@router.callback_query(F.data.regexp(r"^flf:swcamp:(\d+)$"))
async def on_swamp_abandoned_camp(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Заброшенный лагерь на 11–20: предмет или ловушка (1× за проход зоны)."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        parts = str(query.data).split(":")
        if len(parts) != 3 or parts[0] != "flf" or parts[1] != "swcamp":
            await query.answer()
            return
        fl = int(parts[2])
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
        if not rs.is_rotten_swamps_zone(fl):
            await query.answer("Лагерь только на болотах 11–20.", show_alert=True)
            return
        if rs.abandoned_camp_used(char):
            await query.answer("Ты уже обыскал этот лагерь на этом проходе зоны.", show_alert=True)
            return

        rs.set_abandoned_camp_used(char)
        spawns = build_spawns_for_floor(fl)
        ref = next((s for s in spawns if not s.is_elite and not s.is_mini_boss and not s.is_major_boss), None)
        if ref is None and spawns:
            ref = spawns[0]

        slot_b = await inventory_repo.first_free_bag_slot(session, char.id)
        want_loot = random.random() < 0.5

        if want_loot and ref is not None and slot_b is not None:
            payload = loot_tables.roll_victory_item_payload(fl, ref)
            await inventory_repo.add_bag_item(
                session,
                char.id,
                payload,
                bag_slot=slot_b,
            )
            nm = html.escape(str(payload.get("name", "Предмет")))
            note = f"\n{LINE_SEP}\n🏚️ <b>Заброшенный лагерь:</b> удача — <b>{nm}</b> в сумку."
        elif want_loot:
            note = (
                f"\n{LINE_SEP}\n"
                "🏚️ <b>Заброшенный лагерь:</b> в ящике что-то блестит, "
                "но <b>сумка полна</b> — не унести."
            )
        else:
            dmg = max(5, int(char.hp_max) * random.randint(10, 18) // 100)
            char.hp_current = max(1, int(char.hp_current) - dmg)
            note = (
                f"\n{LINE_SEP}\n"
                f"🏚️ <b>Заброшенный лагерь — ловушка:</b> натянутая сеть и гвозди — "
                f"<b>−{dmg} HP</b>."
            )

        await session.flush()
        await push_floor_screen_ui(
            session,
            state,
            query.bot,
            chat_id=query.message.chat.id,
            character=char,
            reply_markup=await floor_keyboard_for_character(session, char),
            target_message=query.message,
            text_suffix=note,
        )
        await query.answer("Лагерь.")
    except Exception:
        logger.exception("flf:swcamp")
        await query.answer("Ошибка.", show_alert=True)


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


@router.callback_query(F.data.regexp(r"^flf:gms:(\d+):([a-z0-9]+):(eat|skip)$"))
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
        if act == "skip":
            note = "🍄 Грибы обошёл — <b>без эффекта</b>."
        else:
            heal = 10 + fl + max(0, (mx - cur) // 12)
            if random.random() < 0.5:
                nh = min(mx, cur + heal)
                char.hp_current = nh
                note = f"🍄 Удача: гриб целебный — <b>+{nh - cur} HP</b>."
            else:
                # Урон по величине совпадает с возможным лечением (та же формула heal).
                new_hp = max(1, cur - heal)
                lost = cur - new_hp
                char.hp_current = new_hp
                note = f"☠️ Яд: гриб был ядовит — <b>−{lost} HP</b>."
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
