"""
Таверна в городах: меню, покупка еды и ночлега (колбэки tvr:*).
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.tavern_kb import tavern_menu_keyboard
from db.repository import character_repo, user_repo
from game.locations import tavern as tavern_loc
from services import tavern_service
from utils.ui import LINE_SEP

router = Router(name="tavern")


async def _load_char(session: AsyncSession, telegram_id: int):
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None
    return await character_repo.get_by_user_id(session, user.id)


@router.callback_query(F.data.startswith("tvr:open:"))
async def tavern_open(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Ты не в этом городе. Обнови /floor.", show_alert=True)
            return
        if not tavern_loc.tavern_available_on_floor(char.floor_number):
            await query.answer("Здесь нет таверны.", show_alert=True)
            return
        text = tavern_service.format_tavern_welcome_html(char)
        await query.message.edit_text(text, reply_markup=tavern_menu_keyboard(char.floor_number))
        await query.answer()
    except Exception:
        logger.exception("tvr:open")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("tvr:buy:"))
async def tavern_buy(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        if len(parts) < 4:
            await query.answer()
            return
        floor_key = int(parts[2])
        offer_key = parts[3]
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Этаж устарел.", show_alert=True)
            return

        ok, payload = await tavern_service.try_buy_offer(session, char, offer_key)
        if not ok:
            await query.answer(payload[:180], show_alert=True)
            return

        header = tavern_service.format_tavern_welcome_html(char)
        await query.message.edit_text(
            f"{header}\n\n{LINE_SEP}\n{payload}",
            reply_markup=tavern_menu_keyboard(char.floor_number),
        )
        await query.answer("Приятного!")
    except Exception:
        logger.exception("tvr:buy")
        await query.answer("Ошибка.", show_alert=True)
