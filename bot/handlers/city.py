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
    temple_skills_shop_keyboard,
)
from bot.states.combat_states import CombatStates
from bot.utils.game_art import menu_city_photo_path
from bot.utils.game_ui import push_game_ui
from db.models.character import Character
from db.repository import character_repo, inventory_repo, user_repo
from game.characters import pets as pets_mod
from game.characters import temple_floor3
from game.floors import floor_data
from services import hub_floor3_npc_service
from services.floor_service import format_city_hub_message
from services import economy_sink_service

router = Router(name="city")


def _temple_skills_shop_html(character: Character, locale: str) -> str:
    from game.characters import player_skills as psk

    loc = "ru"
    psk.ensure_skill_meta(character)
    hint = psk.skill_shop_summary_html(loc)
    return (
        "📜 <b>Школа навыков</b>\n"
        "<i>Деревня «Тихий Ручей», у храма.</i>\n\n"
        f"{hint}\n\n"
        f"💰 <b>Золото:</b> {character.gold}\n"
        "<i>Купленное назначай в статусе → «Навыки».</i>"
    )


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
        if floor_data.get_city_for_floor(char.floor_number) is None:
            await query.answer()
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
    """Рынок этажа 3: лавка, скупщик, банк, храм."""
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
        if floor_key != int(char.floor_number) or int(char.floor_number) != 3:
            await query.answer("Рынок только в деревне на 3 этаже.", show_alert=True)
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

        if act == "skills":
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

            from bot.keyboards.menu_kb import menu_nav_button_row
            from game.archetypes import manager as arc_mgr
            from game.archetypes.data import ARCHETYPES, SKILLS

            arch = arc_mgr.get_character_archetype(char)
            children_keys = arc_mgr.tier2_children(arch.key)
            current_skill_keys = {sk.key for sk in arc_mgr.get_unlocked_skills(char)}
            lvl = int(getattr(char, "level", 1) or 1)
            lines = [
                "📜 <b>Каталог навыков класса</b>",
                f"<i>Архетип:</i> {html_mod.escape(arch.name_ru)} (тир {arch.tier})",
                "",
                "<b>Текущая ветка:</b>",
            ]
            for sk_key in arch.skills:
                sk = SKILLS.get(sk_key)
                if sk is None:
                    continue
                if sk.key in current_skill_keys:
                    flag = "✅"
                else:
                    flag = "🔒"
                lines.append(
                    f"{flag} <b>{html_mod.escape(sk.name_ru)}</b> — "
                    f"{html_mod.escape(sk.description)}",
                )
            if children_keys:
                lines.append("")
                lines.append("<b>Доступные специализации (тир 2):</b>")
                for ck in children_keys:
                    child = ARCHETYPES.get(ck)
                    if child is None:
                        continue
                    req_lvl = int(child.requirements.get("level", 30))
                    open_flag = "✅" if lvl >= req_lvl else f"🔒 ур.{req_lvl}+"
                    lines.append(
                        f"{open_flag} <b>{html_mod.escape(child.name_ru)}</b> "
                        f"<i>{html_mod.escape(child.description)}</i>",
                    )
                    for sk_key in child.skills:
                        sk = SKILLS.get(sk_key)
                        if sk is None:
                            continue
                        lines.append(
                            f"   • {html_mod.escape(sk.name_ru)} — "
                            f"{html_mod.escape(sk.description)}",
                        )
            lines.append("")
            lines.append(
                "<i>Это каталог: навыки открываются по прогрессу персонажа, "
                "покупка отключена.</i>",
            )
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ На рынок", callback_data=f"cty:mkt:{floor_key}:open")],
                    menu_nav_button_row(),
                ],
            )
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text="\n".join(lines),
                reply_markup=kb,
                target_message=query.message,
                photo_path=None,
            )
            await query.answer()
            return

        if act == "scrap":
            from bot.keyboards.scrap_kb import scrap_merchant_keyboard, set_scrap_ui_back
            from services import scrap_merchant_service

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
                        "<i>Дар духов уже с тобой — алтарь молчит. Дальнейшие питомцы — в других городах башни.</i>"
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


@router.callback_query(F.data.startswith("cty:skillbuy:"))
async def on_city_skill_buy(
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
        m = re.match(r"^cty:skillbuy:(\d+):(.+)$", query.data)
        if m is None:
            await query.answer()
            return
        floor_key = int(m.group(1))
        skill_key = m.group(2).strip()
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        loc = get_locale(char, query.from_user.language_code)
        if floor_key != int(char.floor_number) or int(char.floor_number) != 3:
            await query.answer("Школа навыков только в деревне на 3 этаже.", show_alert=True)
            return
        await character_repo.lock_character_row(session, char.id)
        from game.characters import player_skills as psk

        ok, msg = psk.try_buy_temple_skill(char, skill_key)
        await session.flush()
        plain = re.sub(r"<[^>]+>", "", msg)
        if not ok:
            await query.answer(plain[:200] if plain else "Нельзя.", show_alert=True)
            return
        await query.answer(plain[:180] if plain else "Ок.", show_alert=False)
        body = _temple_skills_shop_html(char, loc)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=body,
            reply_markup=temple_skills_shop_keyboard(floor_key, char),
            target_message=query.message,
            photo_path=None,
        )
    except Exception:
        logger.exception("cty:skillbuy")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("cty:skillhave:"))
async def on_city_skill_have(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.data is None or query.from_user is None:
            await query.answer()
            return
        m = re.match(r"^cty:skillhave:(\d+):(.+)$", query.data)
        if m is None:
            await query.answer()
            return
        floor_key = int(m.group(1))
        skill_key = m.group(2).strip()
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        loc = get_locale(char, query.from_user.language_code)
        if floor_key != int(char.floor_number) or int(char.floor_number) != 3:
            await query.answer("Школа навыков только в деревне на 3 этаже.", show_alert=True)
            return
        from game.characters import player_skills as psk

        psk.ensure_skill_meta(char)
        sk = psk.SKILL_BY_KEY.get(skill_key)
        nm = sk.name if sk else skill_key
        hint = f"Уже изучено: {nm}" if loc == "ru" else f"Already learned: {nm}"
        await query.answer(hint[:200], show_alert=True)
    except Exception:
        logger.exception("cty:skillhave")
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
        if char is None or floor_key != int(char.floor_number) or int(char.floor_number) != 3:
            await query.answer("Это только в деревне на 3 этаже.", show_alert=True)
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
