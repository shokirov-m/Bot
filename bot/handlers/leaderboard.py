"""
/top — топ игроков по уровню, этажу, сумме статов и золоту.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.leaderboard_kb import (
    leaderboard_categories_keyboard,
    leaderboard_classes_keyboard,
)
from db.repository import character_repo, leaderboard_repo, user_repo
from services import leaderboard_service

router = Router(name="leaderboard")

_FETCHERS = {
    "lvl": leaderboard_repo.top_by_level,
    "flr": leaderboard_repo.top_by_floor,
    "pow": leaderboard_repo.top_by_stat_sum,
    "gld": leaderboard_repo.top_by_gold,
}


async def _rows_for_category(session: AsyncSession, cat: str) -> list:
    fn = _FETCHERS.get(cat)
    if fn is None:
        return []
    return await fn(session)


INTRO_HTML = (
    "📊 <b>Топ игроков башни</b>\n"
    "Выбери категорию — покажу до 10 лидеров "
    "(забаненные аккаунты скрыты)."
)


@router.message(Command("top"))
@router.message(Command("рейтинг"))
@router.message(Command("топ"))
async def cmd_top(message: Message, session: AsyncSession) -> None:
    try:
        await message.answer(INTRO_HTML, reply_markup=leaderboard_categories_keyboard())
    except Exception:
        logger.exception("Ошибка в /top")


@router.callback_query(F.data.startswith("top:cat:"))
async def on_top_category(query: CallbackQuery, session: AsyncSession) -> None:
    if query.message is None or query.data is None:
        await query.answer()
        return
    try:
        cat = query.data.split(":")[-1]
        
        if cat == "classes":
            await query.message.edit_text(
                "🎭 <b>Топ по классам</b>\nВыбери класс, чтобы увидеть лучших игроков в этой ветке:",
                reply_markup=leaderboard_classes_keyboard()
            )
            await query.answer()
            return
            
        if cat == "clans":
            clans = await leaderboard_repo.top_clans(session)
            text = leaderboard_service.format_clan_leaderboard_html(clans)
            await query.message.edit_text(text, reply_markup=leaderboard_categories_keyboard())
            await query.answer()
            return

        if cat not in _FETCHERS:
            await query.answer()
            return
            
        rows = await _rows_for_category(session, cat)
        loc = "ru"
        if query.from_user is not None:
            user = await user_repo.get_by_telegram_id(session, query.from_user.id)
            ch = await character_repo.get_by_user_id(session, user.id) if user else None
            loc = get_locale(ch, query.from_user.language_code)
        # Загружаем теги кланов для персонажей из топа
        char_ids = [int(c.id) for c in rows]
        clan_tags = await leaderboard_repo.get_clan_tags_for_characters(session, char_ids)
        text = leaderboard_service.format_leaderboard_html(cat, rows, locale=loc, clan_tags=clan_tags)
        kb = leaderboard_categories_keyboard()
        await query.message.edit_text(text, reply_markup=kb)
        await query.answer()
    except Exception:
        logger.exception("top:cat")
        await query.answer("Ошибка рейтинга.", show_alert=True)


@router.callback_query(F.data.startswith("top:class:"))
async def on_top_class(query: CallbackQuery, session: AsyncSession) -> None:
    if query.message is None or query.data is None:
        await query.answer()
        return
    try:
        class_key = query.data.split(":")[-1]
        rows = await leaderboard_repo.top_by_class(session, class_key)
        
        loc = "ru"
        if query.from_user is not None:
            user = await user_repo.get_by_telegram_id(session, query.from_user.id)
            ch = await character_repo.get_by_user_id(session, user.id) if user else None
            loc = get_locale(ch, query.from_user.language_code)
            
        char_ids = [int(c.id) for c in rows]
        clan_tags = await leaderboard_repo.get_clan_tags_for_characters(session, char_ids)
        text = leaderboard_service.format_leaderboard_html(class_key, rows, locale=loc, clan_tags=clan_tags)
        
        await query.message.edit_text(text, reply_markup=leaderboard_classes_keyboard())
        await query.answer()
    except Exception:
        logger.exception("top:class")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "top:back")
async def on_top_back(query: CallbackQuery) -> None:
    if query.message is None:
        await query.answer()
        return
    await query.message.edit_text(INTRO_HTML, reply_markup=leaderboard_categories_keyboard())
    await query.answer()
