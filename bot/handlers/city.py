"""
Городской хаб с этажа (callback fl:{n}:city).
Вынесено из floor.py, чтобы маршрут был явным блоком перед бетой.
"""

from __future__ import annotations

import html as html_mod
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, t
from bot.keyboards.city_kb import city_hub_keyboard
from bot.keyboards.city_market_kb import (
    city_floor3_market_keyboard,
    temple_floor3_keyboard,
)
from bot.states.combat_states import CombatStates
from utils.media.game_art import menu_city_photo_path
from utils.telegram.game_ui import push_game_ui
from db.models.character import Character
from db.repository import character_repo, inventory_repo, user_repo
from game.characters import pets as pets_mod
from game.characters import temple_floor3
from game.tower.progression import floor_data
import services.system.hub_floor3_npc_service as hub_floor3_npc_service
from services.progression.floor_service import format_city_hub_message
import services.economy.economy_sink_service as economy_sink_service

router = Router(name="city")


@router.callback_query(F.data.regexp(r"^fl:(\d+):city$"))
async def on_city_hub_open(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши текущий бой.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        parts = query.data.split(":")
        floor = int(parts[1])
        if floor != char.floor_number:
            await query.answer("Этаж устарел. Открой /floor снова.", show_alert=True)
            return
        city = floor_data.get_city_for_floor(
            int(char.floor_number),
            highest_reached=int(char.highest_floor_reached),
        )
        if city is None:
            await query.answer("Город ещё не открыт — поднимись выше.", show_alert=True)
            return
        loc = get_locale(char, query.from_user.language_code)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=format_city_hub_message(char),
            reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("city hub")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cty:mkt:(\d+)(?::([a-z_]+))?$"))
async def on_city_floor3_market(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Рынок «Тихий Ручей» (якорь 0): лавка, скупщик, банк, храм."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        m = re.match(r"^cty:mkt:(\d+)(?::([a-z_]+))?$", query.data)
        if m is None:
            await query.answer()
            return
        floor_key = int(m.group(1))
        act = (m.group(2) or "open").strip()
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        if not floor_data.city_service_floor_ok(char, floor_key) or floor_key != 0:
            await query.answer("Рынок только в «Тихом Ручье» (первый город-хаб).", show_alert=True)
            return
        loc = get_locale(char, query.from_user.language_code)
        economy_sink_service.clear_bank_ui_back(char)

        if act == "open":
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=(
                    "🏛️ <b>Рынок «Тихий Ручей»</b>\n"
                    "<i>Лавка, скупщик, сейф банка и храм призыва — выбери ниже.</i>"
                ),
                reply_markup=city_floor3_market_keyboard(floor_key),
                target_message=query.message,
                photo_path=menu_city_photo_path(),
                character=char,
            )
            await query.answer()
            return

        if act == "hub":
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=format_city_hub_message(char),
                reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
                target_message=query.message,
                photo_path=menu_city_photo_path(),
                character=char,
            )
            await query.answer()
            return

        if act == "scrap":
            from bot.keyboards.scrap_kb import scrap_merchant_keyboard, set_scrap_ui_back
            import services.economy.scrap_merchant_service as scrap_merchant_service

            await character_repo.lock_character_row(session, char.id)
            set_scrap_ui_back(char, "mkt")
            items = await inventory_repo.list_bag_items(session, char.id)
            text = scrap_merchant_service.format_scrap_menu_html(char, items)
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=text,
                reply_markup=scrap_merchant_keyboard(items, back="mkt"),
                target_message=query.message,
                photo_path=None,
            )
            await query.answer()
            return

        if act == "temple":
            temple_floor3.temple_normalize_legacy(char)
            if temple_floor3.temple_ritual_done(char):
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=(
                        "⛪ <b>Храм призыва</b>\n"
                        "<i>Дар духов уже с тобой — алтарь молчит. Новых питомцев ищи в промо и на этажах 8/48.</i>"
                    ),
                    reply_markup=city_floor3_market_keyboard(floor_key),
                    target_message=query.message,
                    photo_path=menu_city_photo_path(),
                    character=char,
                )
                await query.answer()
                return
            sess = temple_floor3.ensure_temple_session(char)
            await session.flush()
            key = str(sess.get("candidate_key") or "")
            defs = pets_mod._all_defs()
            pet = defs.get(key)
            nm = html_mod.escape(pet.name_ru) if pet else key
            em = pet.emoji if pet else "🐾"
            left = int(sess.get("rerolls_left", 0))
            body = (
                f"⛪ <b>Храм призыва</b>\n"
                f"<i>Один дар — до <b>{temple_floor3.REROLLS_MAX}</b> перебросов.</i>\n\n"
                f"Сейчас: {em} <b>{nm}</b>\n"
                f"Осталось перебросов: <b>{left}</b>"
            )
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=body,
                reply_markup=temple_floor3_keyboard(floor_key, can_reroll=left > 0),
                target_message=query.message,
                photo_path=menu_city_photo_path(),
                character=char,
            )
            await query.answer()
            return

        if act == "temple_rer":
            await character_repo.lock_character_row(session, char.id)
            ok, msg = temple_floor3.try_reroll(char)
            await session.flush()
            if not ok:
                await query.answer(msg[:200], show_alert=True)
                return
            await query.answer(msg[:120], show_alert=False)
            sess = temple_floor3.temple_session(char) or {}
            key = str(sess.get("candidate_key") or "")
            defs = pets_mod._all_defs()
            pet = defs.get(key)
            nm = html_mod.escape(pet.name_ru) if pet else key
            em = pet.emoji if pet else "🐾"
            left = int(sess.get("rerolls_left", 0))
            body = (
                f"⛪ <b>Храм призыва</b>\n"
                f"<i>Один дар — до <b>{temple_floor3.REROLLS_MAX}</b> перебросов.</i>\n\n"
                f"Сейчас: {em} <b>{nm}</b>\n"
                f"Осталось перебросов: <b>{left}</b>"
            )
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=body,
                reply_markup=temple_floor3_keyboard(floor_key, can_reroll=left > 0),
                target_message=query.message,
                photo_path=menu_city_photo_path(),
                character=char,
            )
            return

        if act == "temple_acc":
            await character_repo.lock_character_row(session, char.id)
            ok, msg = temple_floor3.try_accept_temple_pet(char)
            await session.flush()
            plain = re.sub(r"<[^>]+>", "", msg)
            await query.answer(plain[:180] if ok else plain[:200], show_alert=not ok)
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=format_city_hub_message(char) + (f"\n\n{msg}" if msg else ""),
                reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
                target_message=query.message,
                photo_path=None,
            )
            return

        await query.answer()
    except Exception:
        logger.exception("cty:mkt")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cty:f3npc:(scribe|herb):(\d+)$"))
async def on_city_floor3_simple_npc(
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
        m = re.match(r"^cty:f3npc:(scribe|herb):(\d+)$", query.data)
        if m is None:
            await query.answer()
            return
        which = m.group(1)
        floor_key = int(m.group(2))
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None or not floor_data.city_service_floor_ok(char, floor_key) or floor_key != 0:
            await query.answer("Эти NPC только в «Тихом Ручье» (первый город-хаб).", show_alert=True)
            return
        loc = get_locale(char, query.from_user.language_code)
        await character_repo.lock_character_row(session, char.id)
        if which == "scribe":
            ok, msg = await hub_floor3_npc_service.try_scribe_quest(session, char)
        else:
            ok, msg = await hub_floor3_npc_service.try_herbalist_quest(session, char)
        await session.commit()
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        await query.answer("Готово.", show_alert=False)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=format_city_hub_message(char) + f"\n\n{msg}",
            reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
            target_message=query.message,
            photo_path=None,
        )
    except Exception:
        logger.exception("cty:f3npc")
        await query.answer("Ошибка.", show_alert=True)
