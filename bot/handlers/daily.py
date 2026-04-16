"""Ежедневные награды: /daily и колбэки daily:* (нужна подписка на канал)."""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, t
from bot.keyboards.daily_kb import daily_screen_keyboard
from db.repository import character_repo, user_repo
from services import daily_service
from services.daily_screen_service import build_daily_body_html
from services.subscription_service import subscription_check

router = Router(name="daily")


@router.message(Command("daily"))
async def cmd_daily(message: Message, session: AsyncSession) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            await message.answer("Нет доступа.")
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Сначала создай героя через /start.")
            return
        loc = get_locale(char, message.from_user.language_code if message.from_user else None)
        body, sub = await build_daily_body_html(
            message.bot,
            message.from_user.id,
            char,
            locale=loc,
            title_html=t(loc, "daily_header"),
        )
        if not sub:
            await message.answer(
                body,
                parse_mode=ParseMode.HTML,
                reply_markup=daily_screen_keyboard(subscribed=False, can_claim=False, locale=loc),
                disable_web_page_preview=True,
            )
            return
        res = await daily_service.try_claim_daily_reward(session, char, locale=loc, bot=message.bot)
        if res.message_html:
            if res.ok:
                body += "\n\n" + res.message_html
            else:
                body += "\n\n" + f"<i>{html.escape(res.message_html)}</i>"
        await session.commit()
        await message.answer(
            body,
            parse_mode=ParseMode.HTML,
            reply_markup=daily_screen_keyboard(
                subscribed=True,
                can_claim=daily_service.can_claim_daily_today(char),
                locale=loc,
            ),
            disable_web_page_preview=True,
        )
    except Exception:
        logger.exception("cmd_daily")
        await message.answer("Ошибка.")


@router.callback_query(F.data == "daily:verify")
async def daily_verify(callback: CallbackQuery, session: AsyncSession) -> None:
    try:
        if callback.from_user is None or callback.message is None:
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
        loc = get_locale(char, callback.from_user.language_code)
        body, sub = await build_daily_body_html(
            callback.bot,
            callback.from_user.id,
            char,
            locale=loc,
            title_html=t(loc, "daily_header"),
        )
        await callback.message.edit_text(
            body,
            parse_mode=ParseMode.HTML,
            reply_markup=daily_screen_keyboard(
                subscribed=sub,
                can_claim=daily_service.can_claim_daily_today(char) if sub else False,
                locale=loc,
            ),
            disable_web_page_preview=True,
        )
        await callback.answer("Подписка подтверждена!" if sub else "Подписка не найдена или ошибка API.")
        await session.commit()
    except Exception:
        logger.exception("daily:verify")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "daily:claim")
async def daily_claim(callback: CallbackQuery, session: AsyncSession) -> None:
    try:
        if callback.from_user is None or callback.message is None:
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
        loc = get_locale(char, callback.from_user.language_code)
        sub, _hint = await subscription_check(callback.bot, callback.from_user.id, locale=loc)
        if not sub:
            await callback.answer("Сначала подпишись на канал.", show_alert=True)
            return
        res = await daily_service.try_claim_daily_reward(session, char, locale=loc, bot=callback.bot)
        body, _ = await build_daily_body_html(
            callback.bot,
            callback.from_user.id,
            char,
            locale=loc,
            title_html=t(loc, "daily_header"),
        )
        if res.message_html:
            if res.ok:
                body += "\n\n" + res.message_html
            else:
                body += "\n\n" + f"<i>{html.escape(res.message_html)}</i>"
        await callback.message.edit_text(
            body,
            parse_mode=ParseMode.HTML,
            reply_markup=daily_screen_keyboard(
                subscribed=True,
                can_claim=daily_service.can_claim_daily_today(char),
                locale=loc,
            ),
            disable_web_page_preview=True,
        )
        await session.commit()
        await callback.answer("Готово." if res.ok else "Пока нельзя забрать награду.")
    except Exception:
        logger.exception("daily:claim")
        await callback.answer("Ошибка.", show_alert=True)
