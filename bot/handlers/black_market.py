"""Чёрный рынок: хаб, Жабс, NPC-локации."""

from __future__ import annotations

import html
import random

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.black_market_kb import jabs_lots_keyboard, location_back_keyboard, market_hub_keyboard
from utils.telegram.game_ui import push_game_ui
from db.repository import character_repo, user_repo
from game.mercenaries.market_hub import LOCATIONS, dialog_pool, HUB_MECHANICS_RU
from game.mercenaries.shadow_market_meta import (
    get_purchased_showcase_lot_indices,
    mark_showcase_lot_purchased,
    market_hub_session_open,
)
import services.economy.black_market_quest_service as black_market_quest_service
import services.economy.black_market_service as black_market_service
import services.social.mercenary_service as mercenary_service

router = Router(name="black_market")


async def _char(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user is None:
        return None
    user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
    if user is None or getattr(user, "is_banned", False):
        return None
    return await character_repo.get_by_user_id(session, user.id)


def _format_lot_line(i: int, lot: dict) -> str:
    from game.mercenaries.mercenary_classes import role_def
    from game.mercenaries.mercenary_data import RARITY_LABEL_RU

    rd = role_def(str(lot.get("class_role", "dd_phys")))
    rar = RARITY_LABEL_RU.get(str(lot.get("rarity", "common")), "обычный")
    return (
        f"{i + 1}. <b>{html.escape(str(lot.get('display_name', '?')))}</b> — "
        f"{rar}, {html.escape(rd.name_ru)}, ур.{int(lot.get('level', 1))}, "
        f"❤️{int(lot.get('hp_max', 0))} ⚔️{int(lot.get('atk', 0))} — "
        f"<b>{int(lot.get('price_gold', 0)):,}</b> 💰"
    )


@router.callback_query(F.data == "bm:hub")
async def bm_hub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, err = black_market_service.can_enter_market(char)
        if not ok:
            await callback.answer(err or "Нельзя.", show_alert=True)
            return
        if not market_hub_session_open(char):
            await callback.answer("Сначала войди через «Тёмный проход» на 26 этаже.", show_alert=True)
            return
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=black_market_service.format_hub_intro_html(),
            reply_markup=market_hub_keyboard(),
            target_message=callback.message,
            photo_path=None,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("bm:hub")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "bm:jabs")
async def bm_jabs(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not market_hub_session_open(char):
            await callback.answer("Сначала войди через проход на этаже.", show_alert=True)
            return
        sm = await black_market_service.get_or_roll_showcase(session)
        lots = list(sm.get("lots") or [])
        week_id = str(sm.get("week_id") or "")
        bought = get_purchased_showcase_lot_indices(char, week_id)
        available_idx = [i for i in range(len(lots)) if i not in bought]
        if not available_idx:
            lines = [
                "🐸 <b>Жабс</b> моргает третьим глазом: «На этой неделе ты уже скупил всё, что я выставлял. "
                "Загляни в понедельник».",
            ]
        else:
            lines = [
                "🐸 <b>Жабс</b> выставляет наёмников. Витрина обновляется раз в неделю.\n",
                "Каждый лот — один наёмник; купленный лот пропадает <b>для тебя</b> до смены витрины.\n",
                *(_format_lot_line(j, lots[i]) for j, i in enumerate(available_idx)),
            ]
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text="\n".join(lines),
            reply_markup=jabs_lots_keyboard(available_idx),
            target_message=callback.message,
            photo_path=None,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("bm:jabs")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("bm:buy:"))
async def bm_buy(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None or callback.data is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not market_hub_session_open(char):
            await callback.answer("Сессия рынка истекла. Войди снова через проход.", show_alert=True)
            return
        idx = int(callback.data.split(":")[-1])
        sm = await black_market_service.get_or_roll_showcase(session)
        lots = list(sm.get("lots") or [])
        week_id = str(sm.get("week_id") or "")
        if idx < 0 or idx >= len(lots):
            await callback.answer("Лот недоступен.", show_alert=True)
            return
        if idx in get_purchased_showcase_lot_indices(char, week_id):
            await callback.answer("Этот лот ты уже купил.", show_alert=True)
            return
        ok, msg = await mercenary_service.hire_from_lot(session, char, lots[idx])
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        mark_showcase_lot_purchased(char, week_id, idx)
        await session.flush()
        bought = get_purchased_showcase_lot_indices(char, week_id)
        available_idx = [i for i in range(len(lots)) if i not in bought]
        if not available_idx:
            follow = "\n\n🐸 Жабс: «На сегодня с тобой всё — до новой витрины»."
            kb = jabs_lots_keyboard([])
        else:
            follow = ""
            kb = jabs_lots_keyboard(available_idx)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"✅ {msg}\n\n<i>Настрой отряд в Доме → Покои наёмников.</i>{follow}",
            reply_markup=kb,
            target_message=callback.message,
            photo_path=None,
            character=char,
        )
        await callback.answer("Куплено!")
    except Exception:
        logger.exception("bm:buy")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("bm:loc:"))
async def bm_location(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None or callback.data is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not market_hub_session_open(char):
            await callback.answer("Сессия рынка истекла.", show_alert=True)
            return
        key = callback.data.split(":")[-1]
        loc = next((x for x in LOCATIONS if x.key == key), None)
        if loc is None:
            await callback.answer("Нет такого места.", show_alert=True)
            return
        dlg = random.choice(dialog_pool(key))
        body = f"<b>{html.escape(loc.title_ru)}</b>\n<i>{html.escape(loc.intro_ru)}</i>\n\n💬 {html.escape(dlg)}"
        mech = HUB_MECHANICS_RU.get(key)
        if mech:
            body += f"\n\n⚙️ <i>{html.escape(mech)}</i>"

        qk = f"hub_{key}"
        if black_market_quest_service.quest_status(char, qk) != "done":
            black_market_quest_service.start_quest(char, qk)
            reward = 800 if key == "contracts" else 400
            note = black_market_quest_service.complete_quest(char, qk, reward)
            body += f"\n\n📜 <i>{html.escape(note)}</i>"

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=location_back_keyboard(),
            target_message=callback.message,
            photo_path=None,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("bm:loc")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "bm:back_floor")
async def bm_back_floor(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        from services.progression.floor_service import floor_keyboard_for_character, push_floor_screen_ui

        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        black_market_service.close_market_hub_session(char)
        await push_floor_screen_ui(
            session,
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            character=char,
            reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=callback.from_user.id),
            target_message=callback.message,
        )
        await callback.answer()
    except Exception:
        logger.exception("bm:back_floor")
        await callback.answer("Ошибка.", show_alert=True)
