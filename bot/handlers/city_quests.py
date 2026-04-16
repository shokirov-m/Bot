"""Поручения стражи в городах-хабах (колбэки cty:*)."""

from __future__ import annotations

import html
import re

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.city_quest_kb import city_quest_hub_only_keyboard, city_quest_offer_keyboard
from bot.keyboards.forge_kb import city_hub_keyboard
from bot.states.combat_states import CombatStates
from db.repository import character_repo, quest_repo, user_repo
from game.floors import floor_data
from game.quests.city_quests import city_quest_template
from services import city_quest_service
from services.floor_service import format_city_hub_message

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
        if code == "hub":
            await query.message.edit_text(
                format_city_hub_message(char),
                reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
                parse_mode=ParseMode.HTML,
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
                await query.message.edit_text(
                    f"⚔️ <b>Стража</b>\n\n{body}",
                    reply_markup=city_quest_offer_keyboard(char.floor_number),
                )
            elif row.status == "completed":
                await query.message.edit_text(
                    f"🏛️ <b>{html.escape(tpl.title)}</b>\n"
                    "Страж кивает: в этом городе ты уже всё сделал.",
                    reply_markup=city_quest_hub_only_keyboard(char.floor_number),
                )
            else:
                p = dict(row.progress or {})
                k = int(p.get("kills", 0))
                need = int(p.get("need", tpl.kills_needed))
                await query.message.edit_text(
                    f"🏛️ <b>{html.escape(tpl.title)}</b>\n"
                    f"Прогресс: побед в башне — <b>{k}/{need}</b>.\n"
                    "Сражайся на этажах и возвращайся.",
                    reply_markup=city_quest_hub_only_keyboard(char.floor_number),
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
            await query.message.edit_text(
                msg,
                reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
                parse_mode=ParseMode.HTML,
            )
            await query.answer("Поручение записано.")
            return

        await query.answer()
    except Exception:
        logger.exception("cty callback")
        await query.answer("Ошибка.", show_alert=True)
