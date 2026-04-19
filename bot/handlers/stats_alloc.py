"""
Распределение свободных очков характеристик: /stats.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.menu_kb import menu_nav_button_row
from db.repository import character_repo, user_repo
from services import character_service, profession_service, stat_bonus_service

router = Router(name="stats_alloc")


def _stats_text(char) -> str:
    free = int(getattr(char, "unspent_stat_points", 0) or 0)
    if free > 0:
        hint = f"Свободных очков: <b>{free}</b>. Кнопки ниже — по +1 к стату."
    else:
        hint = "Свободных очков нет — повышай уровень в бою и квестах (+5 очков за уровень)."
    return (
        "📊 <b>Характеристики</b>\n"
        f"{hint}\n\n"
        f"⚔️ СИЛ: {char.stat_strength}    🏃 ЛОВ: {char.stat_dexterity}\n"
        f"🔮 ИНТ: {char.stat_intelligence}     🛡️ ВЫН: {char.stat_vitality}\n"
        f"🍀 УДА: {char.stat_luck}\n\n"
        f"❤️ HP: {char.hp_current}/{char.hp_max}    💙 MP: {char.mp_current}/{char.mp_max}"
    )


def stats_keyboard(unspent: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if unspent > 0:
        rows.extend(
            [
                [
                    InlineKeyboardButton(text="+1 СИЛ", callback_data="st:a:str"),
                    InlineKeyboardButton(text="+1 ЛОВ", callback_data="st:a:dex"),
                ],
                [
                    InlineKeyboardButton(text="+1 ИНТ", callback_data="st:a:int"),
                    InlineKeyboardButton(text="+1 ВЫН", callback_data="st:a:vit"),
                ],
                [InlineKeyboardButton(text="+1 УДА", callback_data="st:a:luck")],
            ],
        )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("stats", "статы"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            await message.answer("Сначала /start.")
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Персонаж не создан.")
            return
        usp = int(getattr(char, "unspent_stat_points", 0) or 0)
        await message.answer(
            _stats_text(char),
            reply_markup=stats_keyboard(usp),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("/stats")


@router.callback_query(F.data.startswith("st:a:"))
async def st_allocate(callback: CallbackQuery, session: AsyncSession) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.data is None:
            await callback.answer()
            return
        parts = callback.data.split(":")
        if len(parts) < 3:
            await callback.answer()
            return
        key = parts[2]
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        prior_eff = await stat_bonus_service.effective_primary_stats(session, char)
        if not character_service.try_allocate_stat_point(char, key):
            await callback.answer("Нет свободных очков или неверный стат.", show_alert=True)
            return
        await character_service.refresh_hp_mp_from_effective(session, char, prior_effective_stats=prior_eff)
        profession_service.refresh_unlocks(char)
        await session.flush()
        usp = int(getattr(char, "unspent_stat_points", 0) or 0)
        await callback.message.edit_text(
            _stats_text(char),
            reply_markup=stats_keyboard(usp),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer("+1 к стату")
    except Exception:
        logger.exception("st:a")
        await callback.answer("Ошибка.", show_alert=True)
