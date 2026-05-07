"""
Распределение свободных очков характеристик: /stats.

Поддерживает режимы вложения: +1, +5, +10, +100 за раз.
Активный режим выбирается кнопкой «Режим»; хранится в FSM state (stats_mode).
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.menu_kb import menu_nav_button_row
from bot.utils.game_ui import edit_game_message_content
from db.repository import character_repo, user_repo
from services import character_service, stat_bonus_service

router = Router(name="stats_alloc")

# Доступные режимы вложения
_MODES: list[int] = [1, 5, 10, 100]
_MODE_DEFAULT = 1


def _stats_text(char, mode: int) -> str:
    free = int(getattr(char, "unspent_stat_points", 0) or 0)
    if free > 0:
        hint = (
            f"Свободных очков: <b>{free}</b>. "
            f"Активный режим: <b>+{mode}</b> за нажатие."
        )
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


def stats_keyboard(unspent: int, mode: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    # Переключатель режима — кнопки, у активного режима [✓]
    mode_row: list[InlineKeyboardButton] = []
    for m in _MODES:
        label = f"[+{m}]" if m == mode else f"+{m}"
        mode_row.append(InlineKeyboardButton(text=label, callback_data=f"st:m:{m}"))
    rows.append(mode_row)

    if unspent > 0:
        rows.extend(
            [
                [
                    InlineKeyboardButton(text=f"+{mode} СИЛ", callback_data=f"st:a:str:{mode}"),
                    InlineKeyboardButton(text=f"+{mode} ЛОВ", callback_data=f"st:a:dex:{mode}"),
                ],
                [
                    InlineKeyboardButton(text=f"+{mode} ИНТ", callback_data=f"st:a:int:{mode}"),
                    InlineKeyboardButton(text=f"+{mode} ВЫН", callback_data=f"st:a:vit:{mode}"),
                ],
                [InlineKeyboardButton(text=f"+{mode} УДА", callback_data=f"st:a:luck:{mode}")],
            ],
        )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _get_mode(state: FSMContext) -> int:
    data = await state.get_data()
    m = data.get("stats_mode", _MODE_DEFAULT)
    return m if m in _MODES else _MODE_DEFAULT


@router.message(Command("stats", "статы"))
async def cmd_stats(message: Message, session: AsyncSession, state: FSMContext) -> None:
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
        mode = await _get_mode(state)
        usp = int(getattr(char, "unspent_stat_points", 0) or 0)
        await message.answer(
            _stats_text(char, mode),
            reply_markup=stats_keyboard(usp, mode),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("/stats")


@router.callback_query(F.data.startswith("st:m:"))
async def st_switch_mode(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Переключение режима +1/+5/+10/+100."""
    try:
        if callback.from_user is None or callback.message is None or callback.data is None:
            await callback.answer()
            return
        try:
            new_mode = int(callback.data.split(":")[2])
        except (IndexError, ValueError):
            await callback.answer()
            return
        if new_mode not in _MODES:
            await callback.answer()
            return
        await state.update_data(stats_mode=new_mode)

        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        usp = int(getattr(char, "unspent_stat_points", 0) or 0)
        await edit_game_message_content(callback.message,
            _stats_text(char, new_mode),
            reply_markup=stats_keyboard(usp, new_mode),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer(f"Режим: +{new_mode}")
    except Exception:
        logger.exception("st:m")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("st:a:"))
async def st_allocate(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.data is None:
            await callback.answer()
            return
        parts = callback.data.split(":")
        # формат: st:a:<stat>[:<amount>]
        if len(parts) < 3:
            await callback.answer()
            return
        key = parts[2]
        # Количество берём из callback_data или из FSM state
        if len(parts) >= 4:
            try:
                amount = int(parts[3])
            except ValueError:
                amount = await _get_mode(state)
        else:
            amount = await _get_mode(state)

        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        prior_eff = await stat_bonus_service.effective_primary_stats(session, char)
        spent = character_service.try_allocate_stat_point(char, key, amount)
        if spent == 0:
            await callback.answer("Нет свободных очков или неверный стат.", show_alert=True)
            return

        await character_service.refresh_hp_mp_from_effective(session, char, prior_effective_stats=prior_eff)
        await session.flush()

        mode = await _get_mode(state)
        usp = int(getattr(char, "unspent_stat_points", 0) or 0)
        await edit_game_message_content(callback.message,
            _stats_text(char, mode),
            reply_markup=stats_keyboard(usp, mode),
            parse_mode=ParseMode.HTML,
        )
        # Показываем сколько фактически потрачено (может быть меньше amount если очков не хватало)
        stat_name = {"str": "СИЛ", "dex": "ЛОВ", "int": "ИНТ", "vit": "ВЫН", "luck": "УДА"}.get(key, key.upper())
        await callback.answer(f"+{spent} {stat_name}")
    except Exception:
        logger.exception("st:a")
        await callback.answer("Ошибка.", show_alert=True)
