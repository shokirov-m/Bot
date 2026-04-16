"""
Торговля: лавка на этажах с торговцем и в городах (колбэки shp:*).
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.shop_kb import shop_main_keyboard
from db.repository import character_repo, user_repo
from game.economy import shop as shop_data
from services import shop_service
from utils.ui import LINE_SEP

router = Router(name="shop")


async def _load_char(session: AsyncSession, telegram_id: int):
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None
    return await character_repo.get_by_user_id(session, user.id)


def _origin_ok(s: str) -> str:
    return s if s in ("c", "f") else "f"


@router.callback_query(F.data.startswith("shp:main:"))
async def shop_open(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        origin = _origin_ok(parts[3]) if len(parts) > 3 else "f"
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Ты не здесь. Обнови /floor.", show_alert=True)
            return
        if not shop_data.shop_available_on_floor(char.floor_number):
            await query.answer("Здесь нет торговца.", show_alert=True)
            return
        text = shop_service.format_shop_welcome_html(char, from_city=(origin == "c"))
        await query.message.edit_text(text, reply_markup=shop_main_keyboard(char.floor_number, origin))
        await query.answer()
    except Exception:
        logger.exception("shp:main")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("shp:buy:"))
async def shop_buy(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        if len(parts) < 5:
            await query.answer()
            return
        floor_key = int(parts[2])
        good_key = parts[3]
        origin = _origin_ok(parts[4])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Этаж устарел.", show_alert=True)
            return

        ok, payload = await shop_service.try_buy_good(session, char, good_key, expected_floor=floor_key)
        if not ok:
            await query.answer(payload[:180], show_alert=True)
            return

        header = shop_service.format_shop_welcome_html(char, from_city=(origin == "c"))
        await query.message.edit_text(
            f"{header}\n\n{LINE_SEP}\n{payload}",
            reply_markup=shop_main_keyboard(char.floor_number, origin),
        )
        await query.answer("Куплено!")
    except Exception:
        logger.exception("shp:buy")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("shp:eat:"))
async def shop_eat_ration(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        origin = _origin_ok(parts[3]) if len(parts) > 3 else "f"
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Этаж устарел.", show_alert=True)
            return

        ok, msg = await shop_service.try_use_first_bag_ration(session, char)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return

        header = shop_service.format_shop_welcome_html(char, from_city=(origin == "c"))
        await query.message.edit_text(
            f"{header}\n\n{LINE_SEP}\n{msg}",
            reply_markup=shop_main_keyboard(char.floor_number, origin),
        )
        await query.answer("Вкусно!")
    except Exception:
        logger.exception("shp:eat")
        await query.answer("Ошибка.", show_alert=True)
