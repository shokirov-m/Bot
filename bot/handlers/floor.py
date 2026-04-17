"""
Экран текущего этажа: /floor, навигация по открытым этажам, выбор монстра.
"""

from __future__ import annotations

import html
import random
import re

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.floor_kb import secret_result_keyboard
from bot.keyboards.forest_kb import forest_mushroom_keyboard, forest_spirit_keyboard
from bot.states.combat_states import CombatStates
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, user_repo
from game.characters import pets as pets_mod
from game.floors import floor_data
from game.floors import wandering_npcs as wandering_npcs_mod
from game.floors import forest_beginnings as fb
from game.floors import long_floor as long_floor_mod
from services import combat_service
from services.floor_service import (
    floor_keyboard_for_character,
    get_spawns_for_character,
    push_floor_screen_ui,
    travel_by_delta,
    travel_to_floor,
    try_secret_search,
)
from utils.ui import LINE_SEP

router = Router(name="floor")

_FLOOR_CB = re.compile(r"^fl:(\d+):([a-z0-9_]+)$")
_SCR_CB = re.compile(r"^scr:(\d+|back)$")


@router.message(Command("floor"))
@router.message(Command("этаж"))
async def cmd_floor(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Показать этаж и доступных монстров."""
    try:
        if message.from_user is None:
            return
        tg = message.from_user
        user = await user_repo.get_by_telegram_id(session, tg.id)
        if user is None or user.is_banned:
            await message.answer("Сначала нажми /start.")
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Создай героя через /start.")
            return

        kb = await floor_keyboard_for_character(session, char)
        await push_floor_screen_ui(
            session,
            state,
            message.bot,
            chat_id=message.chat.id,
            character=char,
            reply_markup=kb,
            fallback_message=message,
        )
    except Exception:
        logger.exception("Ошибка в /floor")


@router.callback_query(F.data.in_(("flnav:up", "flnav:dn")))
async def on_floor_nav_step(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.from_user is None or query.message is None or query.data is None:
            await query.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        delta = 1 if query.data == "flnav:up" else -1
        ok, err = await travel_by_delta(
            session,
            char,
            delta,
            telegram_id=query.from_user.id,
            username=query.from_user.username,
            bot=query.bot,
        )
        if not ok:
            await query.answer(err or "Нельзя.", show_alert=True)
            return
        await push_floor_screen_ui(
            session,
            state,
            query.bot,
            chat_id=query.message.chat.id,
            character=char,
            reply_markup=await floor_keyboard_for_character(session, char),
            target_message=query.message,
        )
        await query.answer(f"Этаж {char.floor_number}")
    except Exception:
        logger.exception("flnav")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("scr:"))
async def on_scrap_merchant_callback(
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
        m = _SCR_CB.match(query.data)
        if m is None:
            await query.answer()
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        tok = m.group(1)
        if tok == "back":
            await push_floor_screen_ui(
                session,
                state,
                query.bot,
                chat_id=query.message.chat.id,
                character=char,
                reply_markup=await floor_keyboard_for_character(session, char),
                target_message=query.message,
            )
            await query.answer()
            return
        from bot.keyboards.scrap_kb import scrap_merchant_keyboard
        from db.repository import inventory_repo
        from services import scrap_merchant_service

        ok, msg = await scrap_merchant_service.try_sell_bag_item_by_id(
            session,
            char,
            int(tok),
            telegram_id=query.from_user.id,
            username=query.from_user.username,
            bot=query.bot,
        )
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        await session.refresh(char)
        items = await inventory_repo.list_bag_items(session, char.id)
        text = scrap_merchant_service.format_scrap_menu_html(char, items)
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=scrap_merchant_keyboard(items),
        )
        await query.answer("Продано.", show_alert=False)
    except Exception:
        logger.exception("scr callback")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("fl:"))
async def on_floor_callback(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Выбор цели на этаже — старт боя."""
    try:
        if query.data is None or query.from_user is None:
            await query.answer()
            return

        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши текущий бой.", show_alert=True)
            return

        m = _FLOOR_CB.match(query.data)
        if m is None:
            await query.answer()
            return

        floor = int(m.group(1))
        code = m.group(2)

        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return

        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return

        if floor != char.floor_number:
            await query.answer("Этаж устарел. Открой /floor снова.", show_alert=True)
            return

        if code == "tutorial":
            if int(char.floor_number) != 1:
                await query.answer("Обучение только на 1 этаже.", show_alert=True)
                return
            if query.message is None:
                await query.answer()
                return
            await combat_service.start_tutorial_combat(
                query=query,
                session=session,
                state=state,
                character=char,
            )
            return

        if code == "wnpc":
            info = wandering_npcs_mod.wandering_npc_for_floor(int(char.id), floor)
            if info is None:
                await query.answer("Сейчас здесь никого нет.", show_alert=True)
                return
            msg = f"{info['title']}: {info['hint']}"
            await query.answer(msg[:200], show_alert=True)
            return

        if code in ("petg", "petr", "petw"):
            if query.message is None:
                await query.answer()
                return
            if code in ("petg", "petr"):
                await query.answer(
                    "Призыв питомца — в разделе «Город» (лавка хаба).",
                    show_alert=True,
                )
                return
            else:
                if int(char.floor_number) not in pets_mod.pet_gacha_floors_for_pet_switch():
                    await query.answer()
                    return
                disp = pets_mod.cycle_active_pet(char)
                await session.flush()
                await push_floor_screen_ui(
                    session,
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    character=char,
                    reply_markup=await floor_keyboard_for_character(session, char),
                    target_message=query.message,
                )
                await query.answer(
                    (f"Активен: {disp}" if disp else "Нужно минимум 2 питомца.")[:200],
                    show_alert=True,
                )
                return

        if code == "scrap":
            if query.message is None:
                await query.answer()
                return
            if floor != 3:
                await query.answer("Скупщик только на 3 этаже.", show_alert=True)
                return
            from bot.keyboards.scrap_kb import scrap_merchant_keyboard
            from db.repository import inventory_repo
            from services import scrap_merchant_service

            items = await inventory_repo.list_bag_items(session, char.id)
            text = scrap_merchant_service.format_scrap_menu_html(char, items)
            await query.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=scrap_merchant_keyboard(items),
            )
            await query.answer()
            return

        if code == "classtalk":
            if int(char.floor_number) != 11:
                await query.answer("Наставник только на 11 ярусе.", show_alert=True)
                return
            from game.characters.class_arcs import needs_base_class_choice

            if not needs_base_class_choice(char):
                await query.answer("Твой путь уже определён.", show_alert=True)
                return
            await query.answer(
                "Эрид: «Каждый род ремесла тянет тебя в свою сторону: одни черты окрепнут, "
                "другие ослабнут. Выбери кнопку класса ниже — и не оглядывайся.»",
                show_alert=True,
            )
            return

        if code == "return":
            if query.message is None:
                await query.answer()
                return
            await state.update_data(svc_forest_spirit=None)
            await push_floor_screen_ui(
                session,
                state,
                query.bot,
                chat_id=query.message.chat.id,
                character=char,
                reply_markup=await floor_keyboard_for_character(session, char),
                target_message=query.message,
            )
            await query.answer()
            return

        if code == "ascend":
            if query.message is None:
                await query.answer()
                return
            from game.floors.tower_ascent import tower_next_floor_pending

            pend = tower_next_floor_pending(char)
            if pend is None:
                await query.answer("Сначала победи все цели на этом этаже.", show_alert=True)
                return
            ok, err = await travel_to_floor(
                session,
                char,
                pend,
                telegram_id=query.from_user.id,
                username=query.from_user.username,
                bot=query.bot,
            )
            if not ok:
                await query.answer(err or "Нельзя подняться.", show_alert=True)
                return
            await push_floor_screen_ui(
                session,
                state,
                query.bot,
                chat_id=query.message.chat.id,
                character=char,
                reply_markup=await floor_keyboard_for_character(session, char),
                target_message=query.message,
            )
            await query.answer(f"Этаж {char.floor_number}")
            return

        if code == "down":
            if query.message is None:
                await query.answer()
                return
            ok, err = await travel_by_delta(
                session,
                char,
                -1,
                telegram_id=query.from_user.id,
                username=query.from_user.username,
                bot=query.bot,
            )
            if not ok:
                await query.answer(err or "Нельзя.", show_alert=True)
                return
            await push_floor_screen_ui(
                session,
                state,
                query.bot,
                chat_id=query.message.chat.id,
                character=char,
                reply_markup=await floor_keyboard_for_character(session, char),
                target_message=query.message,
            )
            await query.answer(f"Этаж {char.floor_number}")
            return

        if code in ("lf_keys", "lf_npc", "lf_w1", "lf_w2", "lf_boss"):
            if floor != long_floor_mod.PILOT_FLOOR or not long_floor_mod.is_long_floor_active(char):
                await query.answer("Сценарий «длинного этажа» здесь недоступен.", show_alert=True)
                return
            if query.message is None:
                await query.answer()
                return
            if code == "lf_keys":
                if long_floor_mod.current_phase(char) != "keys":
                    await query.answer("Эта фаза уже пройдена.", show_alert=True)
                    return
                long_floor_mod.advance_from_keys(char)
                await session.flush()
                await push_floor_screen_ui(
                    session,
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    character=char,
                    reply_markup=await floor_keyboard_for_character(session, char),
                    target_message=query.message,
                )
                await query.answer("Ключи найдены.")
                return
            if code == "lf_npc":
                if long_floor_mod.current_phase(char) != "npc":
                    await query.answer("Сначала пройди волны.", show_alert=True)
                    return
                long_floor_mod.advance_from_npc(char)
                await session.flush()
                await push_floor_screen_ui(
                    session,
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    character=char,
                    reply_markup=await floor_keyboard_for_character(session, char),
                    target_message=query.message,
                )
                await query.answer()
                return
            wave_map = {
                "lf_w1": ("wave1", long_floor_mod.SPAWN_W1),
                "lf_w2": ("wave2", long_floor_mod.SPAWN_W2),
                "lf_boss": ("boss", long_floor_mod.SPAWN_BOSS),
            }
            phase_need, spawn = wave_map[code]
            if long_floor_mod.current_phase(char) != phase_need:
                await query.answer("Сначала выполни предыдущий шаг сценария.", show_alert=True)
                return
            await combat_service.start_combat(
                query=query,
                session=session,
                state=state,
                character=char,
                spawn=spawn,
            )
            return

        if code == "srch":
            if query.message is None:
                await query.answer()
                return
            outcome = await try_secret_search(session, char)
            if outcome.alert:
                await query.answer(outcome.alert, show_alert=True)
                return
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=outcome.body_html or "",
                reply_markup=secret_result_keyboard(char.floor_number),
                target_message=query.message,
            )
            await query.answer()
            return

        spawns = get_spawns_for_character(char)
        chosen = next((s for s in spawns if s.slot_code == code), None)
        if chosen is None:
            await query.answer("Цель не найдена.", show_alert=True)
            return

        if query.message is None:
            await query.answer()
            return

        if (
            not long_floor_mod.is_long_floor_active(char)
            and fb.is_forest_beginnings_zone(int(char.floor_number))
            and fb.eligible_for_forest_tricks(chosen)
        ):
            kind = fb.roll_prefight_kind(char)
            if kind == "mushroom":
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=fb.mushroom_intro_html(),
                    reply_markup=forest_mushroom_keyboard(floor, code),
                    target_message=query.message,
                )
                await query.answer()
                return
            if kind == "spirit":
                correct = random.randint(0, 2)
                await state.update_data(
                    svc_forest_spirit={"correct": correct, "slot": chosen.slot_code, "floor": floor},
                )
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=fb.spirit_intro_html(),
                    reply_markup=forest_spirit_keyboard(floor, code),
                    target_message=query.message,
                )
                await query.answer()
                return

        await combat_service.start_combat(
            query=query,
            session=session,
            state=state,
            character=char,
            spawn=chosen,
        )
    except Exception:
        logger.exception("Ошибка в callback этажа")
        await query.answer("Ошибка.", show_alert=True)
