"""Арена теней: /arena, вызов игрока, кнопка меню."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, t
from bot.states.combat_states import CombatStates
from db.models.character import Character
from db.repository import character_repo, user_repo
from services import arena_service

router = Router(name="arena")


def _parse_arena_target(message: Message, command: CommandObject) -> tuple[int | None, str | None, bool]:
    """
    (telegram_id, username, need_help).
    Приоритет: ответ на сообщение → аргумент команды.
    """
    raw_full = (command.args or "").strip()
    if raw_full.lower() in ("help", "помощь", "?"):
        return None, None, True

    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id, None, False

    if not raw_full:
        return None, None, False

    token = raw_full.split()[0].strip().lstrip("@")
    if token.isdigit():
        return int(token), None, False
    return None, token, False


async def _run_arena_for_user(
    *,
    message: Message | None,
    callback: CallbackQuery | None,
    session: AsyncSession,
    state: FSMContext,
    fixed_opponent: Character | None = None,
    command: CommandObject | None = None,
) -> None:
    if await state.get_state() == CombatStates.in_battle.state:
        lang = (
            callback.from_user.language_code
            if callback and callback.from_user
            else (message.from_user.language_code if message and message.from_user else None)
        )
        loc = get_locale(None, lang)
        text = t(loc, "arena_busy")
        if callback:
            await callback.answer(text, show_alert=True)
        elif message:
            await message.answer(text)
        return

    uid = (callback.from_user.id if callback and callback.from_user else None) or (
        message.from_user.id if message and message.from_user else None
    )
    if uid is None:
        return

    user = await user_repo.get_by_telegram_id(session, uid)
    if user is None or user.is_banned:
        if callback:
            await callback.answer("Нет доступа.", show_alert=True)
        return
    char = await character_repo.get_by_user_id(session, user.id)
    if char is None:
        loc = get_locale(None, (callback.from_user if callback else message.from_user).language_code)
        msg = t(loc, "arena_no_char")
        if callback:
            await callback.answer(msg, show_alert=True)
        elif message:
            await message.answer(msg)
        return

    loc = get_locale(char, (callback.from_user if callback else message.from_user).language_code)

    resolved_fixed: Character | None = fixed_opponent
    if message is not None and command is not None:
        tid, uname, need_help = _parse_arena_target(message, command)
        if need_help:
            await message.answer(t(loc, "arena_help"), parse_mode=ParseMode.HTML)
            return
        opp, err_key = await arena_service.resolve_opponent(
            session,
            char,
            telegram_id=tid,
            username=uname,
        )
        if err_key:
            await message.answer(t(loc, err_key), parse_mode=ParseMode.HTML)
            return
        resolved_fixed = opp

    report, gold, outcome = await arena_service.run_shadow_match(session, char, fixed_opponent=resolved_fixed)
    await session.commit()

    header = t(loc, "arena_title")
    if outcome == "win":
        footer = t(loc, "arena_result_win", gold=gold)
    elif outcome == "lose":
        footer = t(loc, "arena_result_lose")
    else:
        footer = t(loc, "arena_draw")
    full = f"{header}\n\n{report}\n\n{footer}"

    if callback and callback.message:
        await callback.message.answer(full, parse_mode=ParseMode.HTML)
        await callback.answer()
    elif message:
        await message.answer(full, parse_mode=ParseMode.HTML)


@router.message(Command("arena"))
async def cmd_arena(message: Message, session: AsyncSession, state: FSMContext, command: CommandObject) -> None:
    try:
        await _run_arena_for_user(
            message=message,
            callback=None,
            session=session,
            state=state,
            command=command,
        )
    except Exception:
        logger.exception("cmd_arena")
        await message.answer("Ошибка арены.")


@router.callback_query(F.data == "mnu:arn")
async def menu_arena(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _run_arena_for_user(
            message=None,
            callback=callback,
            session=session,
            state=state,
            fixed_opponent=None,
        )
    except Exception:
        logger.exception("mnu:arn")
        await callback.answer("Ошибка.", show_alert=True)
