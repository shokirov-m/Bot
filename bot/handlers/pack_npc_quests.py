"""Квесты NPC из паков зон: pqn:hub / pqn:npc / pqn:take / pqn:claim / pqn:back."""

from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db.repository import character_repo, user_repo
from game.tower.quests.pack_npc_quests import quests_for_npc_on_floor
from services.progression.floor_service import floor_keyboard_for_character, push_floor_screen_ui
from services.progression.pack_npc_quest_service import (
    can_claim_quest,
    can_take_quest,
    claim_quest_reward,
    format_hub_html,
    format_npc_html,
    get_quest_state,
    list_npcs_on_floor,
    npc_by_id,
    take_quest,
    zone_key_for_floor,
)
from utils.telegram.game_ui import push_game_ui

router = Router(name="pack_npc_quests")

_PQN = re.compile(r"^pqn:(hub|npc|take|claim|back):(\d+)(?::([a-z0-9_]+))?(?::([a-z0-9_]+))?$")


def _npc_quest_keyboard(character, floor: int, npc_id: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    npc = npc_by_id(floor, npc_id)
    if npc:
        for qdef in quests_for_npc_on_floor(npc, floor):
            qid = str(qdef.get("id") or "")
            title = str(qdef.get("title") or qid)
            if len(title) > 24:
                title = title[:21] + "…"
            st = get_quest_state(character, qid)
            if st is None and can_take_quest(character, floor, npc_id, qid):
                rows.append([
                    InlineKeyboardButton(
                        text=f"📜 {title}",
                        callback_data=f"pqn:take:{floor}:{npc_id}:{qid}",
                    ),
                ])
            elif can_claim_quest(character, qid):
                rows.append([
                    InlineKeyboardButton(
                        text=f"🎁 {title}",
                        callback_data=f"pqn:claim:{floor}:{npc_id}:{qid}",
                    ),
                ])
    rows.append([
        InlineKeyboardButton(text="⬅ К мастерам", callback_data=f"pqn:hub:{floor}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("pqn:"))
async def on_pack_npc_quest_callback(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    m = _PQN.match(query.data or "")
    if m is None:
        await query.answer()
        return
    action, floor_s, npc_id, quest_id = m.group(1), m.group(2), m.group(3), m.group(4)
    floor = int(floor_s)
    if query.from_user is None or query.message is None:
        await query.answer()
        return
    user = await user_repo.get_by_telegram_id(session, query.from_user.id)
    if user is None or user.is_banned:
        await query.answer("Нет доступа.", show_alert=True)
        return
    char = await character_repo.get_by_user_id(session, user.id)
    if char is None:
        await query.answer("Сначала /start.", show_alert=True)
        return
    if int(char.floor_number) != floor:
        await query.answer("Этаж устарел.", show_alert=True)
        return
    if zone_key_for_floor(floor) is None:
        await query.answer("Здесь нет мастеров пака.", show_alert=True)
        return

    try:
        if action == "back":
            kb = await floor_keyboard_for_character(
                session, char, telegram_user_id=query.from_user.id,
            )
            await push_floor_screen_ui(
                session,
                state,
                query.bot,
                chat_id=query.message.chat.id,
                character=char,
                reply_markup=kb,
                target_message=query.message,
            )
            await query.answer()
            return

        if action == "hub":
            text = format_hub_html(char, floor)
            rows: list[list[InlineKeyboardButton]] = []
            for npc in list_npcs_on_floor(floor):
                nid = str(npc.get("id") or "")
                label = f"{npc.get('emoji', '👤')} {npc.get('name', nid)}"
                if len(label) > 28:
                    label = label[:25] + "…"
                rows.append([
                    InlineKeyboardButton(
                        text=label,
                        callback_data=f"pqn:npc:{floor}:{nid}",
                    ),
                ])
            rows.append([
                InlineKeyboardButton(text="⬅ На этаж", callback_data=f"pqn:back:{floor}"),
            ])
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                target_message=query.message,
            )
            await query.answer()
            return

        if action == "npc" and npc_id:
            text = format_npc_html(char, floor, npc_id)
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=text,
                reply_markup=_npc_quest_keyboard(char, floor, npc_id),
                target_message=query.message,
            )
            await query.answer()
            return

        if action == "take" and npc_id and quest_id:
            ok = take_quest(char, floor, npc_id, quest_id)
            await query.answer("Поручение принято." if ok else "Нельзя взять.", show_alert=not ok)
            if ok:
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=format_npc_html(char, floor, npc_id),
                    reply_markup=_npc_quest_keyboard(char, floor, npc_id),
                    target_message=query.message,
                )
            return

        if action == "claim" and npc_id and quest_id:
            ok, msg = await claim_quest_reward(session, char, floor, npc_id, quest_id)
            await query.answer(msg[:200], show_alert=not ok)
            if ok:
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=format_npc_html(char, floor, npc_id),
                    reply_markup=_npc_quest_keyboard(char, floor, npc_id),
                    target_message=query.message,
                )
            return
    except Exception:
        logger.exception("pack_npc_quest callback")
        await query.answer("Ошибка.", show_alert=True)
        return

    await query.answer()
