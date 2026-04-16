"""
/top — топ игроков по уровню, этажу, сумме статов и золоту.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.leaderboard_kb import leaderboard_categories_keyboard
from db.repository import leaderboard_repo
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
        if cat not in _FETCHERS:
            await query.answer()
            return
        rows = await _rows_for_category(session, cat)
        text = leaderboard_service.format_leaderboard_html(cat, rows)
        kb = leaderboard_categories_keyboard()
        await query.message.edit_text(text, reply_markup=kb)
        await query.answer()
    except Exception:
        logger.exception("top:cat")
        await query.answer("Ошибка рейтинга.", show_alert=True)
