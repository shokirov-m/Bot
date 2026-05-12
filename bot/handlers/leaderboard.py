"""
/top — топ игроков по уровню, этажу, сумме статов и золоту.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.leaderboard_kb import (
    leaderboard_categories_keyboard,
    leaderboard_classes_keyboard,
)
from bot.utils.game_art import menu_leaderboard_photo_path
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, leaderboard_repo, user_repo
from services import leaderboard_service
from aiogram.fsm.context import FSMContext

router = Router(name="leaderboard")

_FETCHERS = {
    "lvl": leaderboard_repo.top_by_level,
    "flr": leaderboard_repo.top_by_floor,
    "pow": leaderboard_repo.top_by_stat_sum,
    "gld": leaderboard_repo.top_by_gold,
    "col": leaderboard_repo.top_by_coliseum,
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
        await message.answer(
            INTRO_HTML,
            reply_markup=leaderboard_categories_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("Ошибка в /top")


@router.callback_query(F.data.startswith("top:cat:"))
async def on_top_category(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if query.message is None or query.data is None:
        await query.answer()
        return
    try:
        cat = query.data.split(":")[-1]
        loc = "ru"
        char = None
        if query.from_user is not None:
            user = await user_repo.get_by_telegram_id(session, query.from_user.id)
            char = await character_repo.get_by_user_id(session, user.id) if user else None
            loc = get_locale(char, query.from_user.language_code)
        
        if cat == "classes":
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text="🎭 <b>Топ по классам</b>\nВыбери класс, чтобы увидеть лучших игроков в этой ветке:",
                reply_markup=leaderboard_classes_keyboard(),
                target_message=query.message,
                photo_path=menu_leaderboard_photo_path(),
                character=char,
            )
            await query.answer()
            return
            
        if cat == "clans":
            clans = await leaderboard_repo.top_clans(session)
            text = leaderboard_service.format_clan_leaderboard_html(clans)
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=text,
                reply_markup=leaderboard_categories_keyboard(),
                target_message=query.message,
                photo_path=menu_leaderboard_photo_path(),
                character=char,
            )
            await query.answer()
            return

        if cat == "wsp":
            from datetime import UTC, datetime, timedelta

            from db.models.app_global import AppGlobal
            from services.workshop_leaderboard_service import cached_leaderboard_html, refresh_leaderboards

            row = await session.get(AppGlobal, 1)
            payload = dict(row.payload or {}) if row is not None else {}
            raw_lb = payload.get("workshop_lb_v1") or {}
            ts = str(raw_lb.get("updated_at") or "")
            stale = True
            try:
                t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=UTC)
                stale = datetime.now(UTC) - t > timedelta(seconds=300)
            except (ValueError, TypeError):
                stale = True
            if stale:
                await refresh_leaderboards(session)
                await session.flush()
                row = await session.get(AppGlobal, 1)
                payload = dict(row.payload or {}) if row is not None else {}
            body = cached_leaderboard_html(payload)
            text = f"🏆 <b>Топ мастеров мастерской</b>\n\n{body}"
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=text,
                reply_markup=leaderboard_categories_keyboard(),
                target_message=query.message,
                photo_path=menu_leaderboard_photo_path(),
                character=char,
            )
            await query.answer()
            return

        if cat not in _FETCHERS:
            await query.answer()
            return
            
        rows = await _rows_for_category(session, cat)
        # Загружаем теги кланов для персонажей из топа
        char_ids = [int(c.id) for c in rows]
        clan_tags = await leaderboard_repo.get_clan_tags_for_characters(session, char_ids)
        text = leaderboard_service.format_leaderboard_html(cat, rows, locale=loc, clan_tags=clan_tags)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=leaderboard_categories_keyboard(),
            target_message=query.message,
            photo_path=menu_leaderboard_photo_path(),
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("top:cat")
        await query.answer("Ошибка рейтинга.", show_alert=True)


@router.callback_query(F.data.startswith("top:class:"))
async def on_top_class(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if query.message is None or query.data is None:
        await query.answer()
        return
    try:
        class_key = query.data.split(":")[-1]
        rows = await leaderboard_repo.top_by_class(session, class_key)
        
        loc = "ru"
        char = None
        if query.from_user is not None:
            user = await user_repo.get_by_telegram_id(session, query.from_user.id)
            char = await character_repo.get_by_user_id(session, user.id) if user else None
            loc = get_locale(char, query.from_user.language_code)
            
        char_ids = [int(c.id) for c in rows]
        clan_tags = await leaderboard_repo.get_clan_tags_for_characters(session, char_ids)
        text = leaderboard_service.format_leaderboard_html(class_key, rows, locale=loc, clan_tags=clan_tags)
        
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=leaderboard_classes_keyboard(),
            target_message=query.message,
            photo_path=menu_leaderboard_photo_path(),
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("top:class")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "top:back")
async def on_top_back(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if query.message is None:
        await query.answer()
        return
    char = None
    if query.from_user is not None:
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id) if user else None
    await push_game_ui(
        state,
        query.bot,
        chat_id=query.message.chat.id,
        text=INTRO_HTML,
        reply_markup=leaderboard_categories_keyboard(),
        target_message=query.message,
        photo_path=menu_leaderboard_photo_path(),
        character=char,
    )
    await query.answer()
