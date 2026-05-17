"""Поручения стражи в городах-хабах (колбэки cty:*)."""

from __future__ import annotations

import html
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.city_quest_kb import city_quest_hub_only_keyboard, city_quest_offer_keyboard
from bot.keyboards.forge_kb import city_hub_keyboard
from bot.states.combat_states import CombatStates
from utils.telegram.game_ui import push_game_ui
from db.repository import character_repo, quest_repo, user_repo
from game.tower.progression import floor_data
from game.quests.city_quests import city_quest_template
import services.progression.city_quest_service as city_quest_service
from services.progression.floor_service import format_city_hub_message

router = Router(name="city_quests")

_CTY = re.compile(r"^cty:(\d+):(view|acc|hub)$")


@router.callback_query(F.data.regexp(r"^cty:(\d+):(view|acc|hub)$"))
async def on_city_quest_callback(
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

        m = _CTY.match(query.data)
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
            await query.answer("Город устарел. Открой /floor.", show_alert=True)
            return

        if floor_data.get_city_for_floor(char.floor_number) is None:
            await query.answer("Здесь нет городской стражи.", show_alert=True)
            return

        tpl = city_quest_template(char.floor_number)
        if tpl is None:
            await query.answer("Нет поручения.", show_alert=True)
            return

        loc = get_locale(char, query.from_user.language_code)
        pending_msg = await city_quest_service.try_claim_pending_rewards(session, char)

        if code == "hub":
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=format_city_hub_message(char) + pending_msg,
                reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
                target_message=query.message,
                photo_path=None,
            )
            await query.answer()
            return

        if code == "view":
            row = await quest_repo.get_by_key(session, char.id, tpl.quest_key)
            if row is None:
                body = city_quest_service.offer_screen_html(char.floor_number)
                if body is None:
                    await query.answer("Нет поручения.", show_alert=True)
                    return
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=f"⚔️ <b>Стража</b>\n\n{body}{pending_msg}",
                    reply_markup=city_quest_offer_keyboard(char.floor_number),
                    target_message=query.message,
                    photo_path=None,
                )
            elif row.status == "completed":
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=(
                        f"🏛️ <b>{html.escape(tpl.title)}</b>\n"
                        f"Страж кивает: в этом городе ты уже всё сделал.{pending_msg}"
                    ),
                    reply_markup=city_quest_hub_only_keyboard(char.floor_number),
                    target_message=query.message,
                    photo_path=None,
                )
            else:
                p = dict(row.progress or {})
                k = int(p.get("kills", 0))
                need = int(p.get("need", tpl.kills_needed))
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=(
                        f"🏛️ <b>{html.escape(tpl.title)}</b>\n"
                        f"Прогресс: побед в башне — <b>{k}/{need}</b>.\n"
                        f"Сражайся на этажах и возвращайся.{pending_msg}"
                    ),
                    reply_markup=city_quest_hub_only_keyboard(char.floor_number),
                    target_message=query.message,
                    photo_path=None,
                )
            await query.answer()
            return

        if code == "acc":
            await character_repo.lock_character_row(session, char.id)
            ok, msg = await city_quest_service.try_accept_quest(session, char, char.floor_number)
            if not ok:
                short = msg.replace("<b>", "").replace("</b>", "")[:160]
                await query.answer(short, show_alert=True)
                return
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=msg,
                reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
                target_message=query.message,
                photo_path=None,
            )
            await query.answer("Поручение записано.")
            return

        await query.answer()
    except Exception:
        logger.exception("cty callback")
        await query.answer("Ошибка.", show_alert=True)
