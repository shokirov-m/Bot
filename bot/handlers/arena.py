"""Арена: /arena, вызов по игровому ID или Telegram, кнопка меню."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, t
from bot.states.combat_states import CombatStates
from bot.utils.game_ui import push_game_ui
from db.models.character import Character
from db.repository import character_repo, user_repo
from services import arena_service

router = Router(name="arena")


def _parse_arena_target(
    message: Message,
    command: CommandObject,
) -> tuple[int | None, str | None, int | None, bool]:
    """
    (telegram_id, username, digit_token, need_help).
    digit_token — только если в аргументе одно число (игровой ID или fallback Telegram).
    Ответ на сообщение → всегда telegram_id соперника.
    """
    raw_full = (command.args or "").strip()
    if raw_full.lower() in ("help", "помощь", "?"):
        return None, None, None, True

    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id, None, None, False

    if not raw_full:
        return None, None, None, False

    token = raw_full.split()[0].strip().lstrip("@")
    if token.isdigit():
        return None, None, int(token), False
    return None, token, None, False


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
        tid, uname, digit_tok, need_help = _parse_arena_target(message, command)
        if need_help:
            await message.answer(t(loc, "arena_help"), parse_mode=ParseMode.HTML)
            return
        if digit_tok is not None:
            opp, err_key = await arena_service.resolve_opponent_digit_token(session, char, digit_tok)
        else:
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
        if callback.message is None or callback.from_user is None or callback.bot is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "arena_busy"), show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            loc = get_locale(None, callback.from_user.language_code)
            await callback.answer(t(loc, "arena_no_char"), show_alert=True)
            return
        loc = get_locale(char, callback.from_user.language_code)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(loc, "arena_random_btn"),
                        callback_data="arn:rand",
                    ),
                ],
            ],
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=t(loc, "arena_menu_intro"),
            reply_markup=kb,
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("mnu:arn")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "arn:rand")
async def arena_random_duel(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _run_arena_for_user(
            message=None,
            callback=callback,
            session=session,
            state=state,
            fixed_opponent=None,
            command=None,
        )
    except Exception:
        logger.exception("arn:rand")
        await callback.answer("Ошибка.", show_alert=True)
