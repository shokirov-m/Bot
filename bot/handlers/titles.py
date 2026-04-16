"""
/titles — список открытых титулов и смена отображаемого в профиле.
"""

from __future__ import annotations

import html
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.menu_kb import main_menu_keyboard
from bot.keyboards.title_kb import titles_pick_keyboard
from db.repository import character_repo, user_repo
from game.characters.titles import TITLE_BY_KEY, format_title_bonus_line
from services import title_service
from utils.ui import LINE_SEP

router = Router(name="titles")

_EQ = re.compile(r"^ttl:eq:([\w_]+)$")


def _screen_html(character) -> str:  # noqa: ANN001
    title_service.refresh_unlocks(character)
    keys = title_service.unlocked_sorted(character)
    current = html.escape(character.active_title) if character.active_title else "—"

    if not keys:
        return (
            "🏆 <b>Титулы</b>\n"
            f"{LINE_SEP}\n"
            f"Сейчас в профиле: <b>{current}</b>\n\n"
            "<i>Пока ни одного. Побеждай в боях, поднимайся по башне, "
            "завершай поручения странников, навещай таверну и кузницу.</i>"
        )

    lines = [
        "🏆 <b>Титулы</b>",
        LINE_SEP,
        f"Сейчас в профиле: <b>{current}</b>",
        "",
        "<b>Твои открытые:</b>",
    ]
    for k in keys:
        t = TITLE_BY_KEY[k]
        lines.append(
            f"• <b>{html.escape(t.name_ru)}</b>\n"
            f"  <i>Бонус:</i> {html.escape(format_title_bonus_line(t))}",
        )
    lines.append("")
    lines.append("Нажми титул ниже, чтобы показать его в профиле и включить бонус.")
    return "\n".join(lines)


@router.message(Command("titles"))
@router.message(Command("титулы"))
async def cmd_titles(message: Message, session: AsyncSession) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            await message.answer("Сначала /start.")
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Создай героя через /start.")
            return
        text = _screen_html(char)
        keys = title_service.unlocked_sorted(char)
        loc = get_locale(char, message.from_user.language_code)
        kb = titles_pick_keyboard(keys) if keys else main_menu_keyboard(locale=loc)
        await message.answer(text, reply_markup=kb)
    except Exception:
        logger.exception("Ошибка в /titles")


@router.callback_query(F.data.startswith("ttl:"))
async def on_title_callback(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.from_user is None or query.message is None:
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

        data = query.data or ""

        if data == "ttl:clr":
            title_service.clear_active(char)
            await session.flush()
            text = _screen_html(char)
            keys = title_service.unlocked_sorted(char)
            kb = titles_pick_keyboard(keys) if keys else None
            await query.message.edit_text(text, reply_markup=kb)
            await query.answer("Титул снят.")
            return

        m = _EQ.match(data)
        if m is None:
            await query.answer()
            return

        key = m.group(1)
        ok, _name = title_service.equip(char, key)
        if not ok:
            await query.answer("Титул недоступен.", show_alert=True)
            return
        await session.flush()
        text = _screen_html(char)
        keys = title_service.unlocked_sorted(char)
        await query.message.edit_text(text, reply_markup=titles_pick_keyboard(keys))
        await query.answer("Титул установлен.")
    except Exception:
        logger.exception("ttl callback")
        await query.answer("Ошибка.", show_alert=True)
