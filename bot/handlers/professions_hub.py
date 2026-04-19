"""
Экран профессий (меню и колбэки prn:*).
"""

from __future__ import annotations

import html
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, t
from bot.keyboards.menu_kb import main_menu_keyboard
from bot.keyboards.profession_kb import professions_pick_keyboard
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, user_repo
from game.characters.player_skills import ensure_skill_meta
from game.characters.professions import SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR
from services import profession_service

router = Router(name="professions_hub")


def professions_screen_html(character, *, locale: str, page: int = 0) -> str:  # noqa: ARG001
    loc = locale if locale in ("ru", "en") else "ru"
    profession_service.ensure_profession_meta(character)
    profession_service.refresh_unlocks(character)
    pk = profession_service.active_primary_key(character)
    sk = profession_service.active_secondary_key(character)
    pn = (
        html.escape(profession_service.profession_display_name(pk, locale=loc))
        if pk
        else ("—" if loc == "ru" else "—")
    )
    sn = (
        html.escape(profession_service.profession_display_name(sk, locale=loc))
        if sk
        else ("—" if loc == "ru" else "—")
    )
    intro = t(loc, "professions_screen_intro", floor=SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR)
    eq = t(loc, "professions_equipped_line", p=pn, s=sn)
    keys = profession_service.sorted_unlocked_defs(character)
    if not keys:
        empty = (
            "<i>Пока ни одной. Прокачивай базовые статы и посещай кузницу — см. условия в новостях "
            "или подсказках башни.</i>"
            if loc == "ru"
            else "<i>None yet. Raise base stats and use the forge — see tower hints.</i>"
        )
        return (
            f"{t(loc, 'professions_screen_title')}\n\n"
            f"{intro}\n\n{eq}\n\n{empty}"
        )
    lines = [
        t(loc, "professions_screen_title"),
        "",
        intro,
        "",
        eq,
        "",
        "<b>Открытые:</b>",
    ]
    for d in keys:
        nm = html.escape(profession_service.profession_display_name(d.key, locale=loc))
        lines.append(f"• {nm}")
    lines.append("")
    lines.append(
        "<i>① основная · ② вторая (пассивы половиной)</i>"
        if loc == "ru"
        else "<i>① primary · ② secondary (half passives)</i>",
    )
    return "\n".join(lines)


async def _push_prof_screen(
    *,
    query: CallbackQuery,
    state: FSMContext,
    char,
    page: int,
) -> None:
    assert query.message is not None and query.bot is not None
    profession_service.ensure_profession_meta(char)
    keys_list = [d.key for d in profession_service.sorted_unlocked_defs(char)]
    loc = get_locale(char, query.from_user.language_code if query.from_user else None)
    pg = page if keys_list else 0
    text = professions_screen_html(char, locale=loc, page=pg)
    kb = (
        professions_pick_keyboard(keys_list, page=pg, locale=loc)
        if keys_list
        else main_menu_keyboard(locale=loc)
    )
    await push_game_ui(
        state,
        query.bot,
        chat_id=query.message.chat.id,
        text=text,
        reply_markup=kb,
        target_message=query.message,
        photo_path=None,
    )


@router.callback_query(F.data == "mnu:prof")
async def menu_professions(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Сначала /start.", show_alert=True)
            return
        await _push_prof_screen(query=callback, state=state, char=char, page=0)
        await callback.answer()
    except Exception:
        logger.exception("mnu:prof")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prn:noop")
async def on_prof_page_noop(query: CallbackQuery) -> None:
    await query.answer()


@router.callback_query(F.data.regexp(r"^prn:pg:\d+$"))
async def on_prof_page_turn(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.from_user is None or query.message is None or query.data is None:
            await query.answer()
            return
        tail = query.data.removeprefix("prn:pg:")
        if not tail.isdigit():
            await query.answer()
            return
        page = int(tail)
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        await _push_prof_screen(query=query, state=state, char=char, page=page)
        await query.answer()
    except Exception:
        logger.exception("prn:pg")
        await query.answer("Ошибка.", show_alert=True)


_EQ = re.compile(r"^prn:([12]):([a-z_]+)$")


@router.callback_query(F.data.in_(("prn:clr1", "prn:clr2")))
async def on_prof_clear_slot(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.from_user is None or query.message is None or query.data is None:
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
        loc = get_locale(char, query.from_user.language_code if query.from_user else None)
        if query.data == "prn:clr1":
            ok, err = profession_service.set_active_primary(char, None)
            if not ok:
                await query.answer(err or "Нельзя.", show_alert=True)
                return
            ensure_skill_meta(char)
            await session.flush()
            await _push_prof_screen(query=query, state=state, char=char, page=0)
            await query.answer("Основная снята." if loc == "ru" else "Primary cleared.")
            return
        ok, err = profession_service.set_active_secondary(char, None)
        if not ok:
            await query.answer(err or "Нельзя.", show_alert=True)
            return
        await session.flush()
        await _push_prof_screen(query=query, state=state, char=char, page=0)
        await query.answer("Вторая снята." if loc == "ru" else "Secondary cleared.")
    except Exception:
        logger.exception("prn clr")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^prn:[12]:[a-z_]+$"))
async def on_prof_equip_slot(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.from_user is None or query.message is None or query.data is None:
            await query.answer()
            return
        m = _EQ.match(query.data)
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
        slot = int(m.group(1))
        key = m.group(2)
        if slot == 1:
            ok, err = profession_service.set_active_primary(char, key)
        else:
            ok, err = profession_service.set_active_secondary(char, key)
        if not ok:
            await query.answer(err or "Нельзя.", show_alert=True)
            return
        ensure_skill_meta(char)
        await session.flush()
        await _push_prof_screen(query=query, state=state, char=char, page=0)
        loc = get_locale(char, query.from_user.language_code if query.from_user else None)
        await query.answer("Готово." if loc == "ru" else "Done.")
    except Exception:
        logger.exception("prn equip")
        await query.answer("Ошибка.", show_alert=True)
