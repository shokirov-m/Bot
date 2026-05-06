"""
Городская экономика: лотерея, ростовщик, сейф банка.
Колбэки ecy:* — только на этаже городского хаба.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.economy_kb import bank_safe_keyboard, economy_hub_keyboard
from bot.keyboards.forge_kb import city_hub_keyboard
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, user_repo
from game.economy import sinks as sink_rules
from game.floors import floor_data
from services import economy_sink_service

router = Router(name="economy_sinks")


def _is_message_not_modified(exc: Exception) -> bool:
    return isinstance(exc, TelegramBadRequest) and "message is not modified" in str(exc).lower()


async def _load_char(session: AsyncSession, telegram_id: int):
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None
    return await character_repo.get_by_user_id(session, user.id)


async def _load_char_for_mutation(session: AsyncSession, telegram_id: int):
    """Персонаж + блокировка строки до commit (meta_progress без гонок)."""
    char = await _load_char(session, telegram_id)
    if char is not None:
        await character_repo.lock_character_row(session, char.id)
    return char


@router.callback_query(F.data.startswith("ecy:hub:"))
async def economy_open_hub(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key or floor_data.get_city_for_floor(char.floor_number) is None:
            await query.answer("Город недоступен здесь. Обнови этаж.", show_alert=True)
            return
        economy_sink_service.clear_bank_ui_back(char)
        text = economy_sink_service.economy_hub_intro_html(char)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=economy_hub_keyboard(floor_key),
            target_message=query.message,
            photo_path=None,
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("ecy:hub")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:back:"))
async def economy_back_city(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
            await query.answer("Этаж устарел.", show_alert=True)
            return
        from services.floor_service import format_city_hub_message

        loc = get_locale(char, query.from_user.language_code)
        economy_sink_service.clear_bank_ui_back(char)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=format_city_hub_message(char),
            reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
            target_message=query.message,
            photo_path=None,
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("ecy:back")
        await query.answer("Ошибка.", show_alert=True)


async def _refresh_economy_screen(state: FSMContext, query: CallbackQuery, char, floor_key: int) -> None:
    if query.message is None:
        return
    text = economy_sink_service.economy_hub_intro_html(char)
    await push_game_ui(
        state,
        query.bot,
        chat_id=query.message.chat.id,
        text=text,
        reply_markup=economy_hub_keyboard(floor_key),
        target_message=query.message,
        photo_path=None,
        character=char,
    )


async def _refresh_bank_safe_screen(state: FSMContext, query: CallbackQuery, char, floor_key: int) -> None:
    if query.message is None:
        return
    text = economy_sink_service.bank_safe_intro_html(char)
    bb = economy_sink_service.bank_ui_back(char)
    has_term = sink_rules.bank_term_state(char) is not None
    has_pi = sink_rules.bank_pending_interest(char) > 0
    seal = sink_rules.bank_seal_active(char)
    await push_game_ui(
        state,
        query.bot,
        chat_id=query.message.chat.id,
        text=text,
        reply_markup=bank_safe_keyboard(
            floor_key,
            bank_back=bb,
            has_term=has_term,
            has_pending_interest=has_pi,
            seal_active=seal,
        ),
        target_message=query.message,
        photo_path=None,
        character=char,
    )


@router.callback_query(F.data.startswith("ecy:lot:"))
async def economy_lottery(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = economy_sink_service.try_play_lottery(char, floor_key=floor_key)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        await economy_sink_service.flush(session, char)
        await _refresh_economy_screen(state, query, char, floor_key)
        await query.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("ecy:lot")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:mlb:"))
async def economy_borrow(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = economy_sink_service.try_borrow_moneylender(char, floor_key=floor_key)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        await economy_sink_service.flush(session, char)
        await _refresh_economy_screen(state, query, char, floor_key)
        await query.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("ecy:mlb")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:mlr:"))
async def economy_repay(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = economy_sink_service.try_repay_moneylender(char, floor_key=floor_key)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        await economy_sink_service.flush(session, char)
        await _refresh_economy_screen(state, query, char, floor_key)
        await query.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("ecy:mlr")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:sfv:"))
async def economy_safe_view(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key or floor_data.get_city_for_floor(char.floor_number) is None:
            await query.answer("Город недоступен здесь. Обнови этаж.", show_alert=True)
            return
        if len(parts) > 3 and parts[3] == "mkt":
            economy_sink_service.set_bank_ui_back(char, "mkt")
        else:
            economy_sink_service.set_bank_ui_back(char, "hub")
        await economy_sink_service.flush(session, char)
        await _refresh_bank_safe_screen(state, query, char, floor_key)
        await query.answer()
    except Exception:
        logger.exception("ecy:sfv")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:sfd:"))
async def economy_safe_deposit(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        amount = int(parts[3])
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = economy_sink_service.try_bank_safe_deposit(char, floor_key=floor_key, amount=amount)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        await economy_sink_service.flush(session, char)
        await _refresh_bank_safe_screen(state, query, char, floor_key)
        await query.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("ecy:sfd")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:sfw:"))
async def economy_safe_withdraw(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        amount = int(parts[3])
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = economy_sink_service.try_bank_safe_withdraw(char, floor_key=floor_key, amount=amount)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        await economy_sink_service.flush(session, char)
        await _refresh_bank_safe_screen(state, query, char, floor_key)
        await query.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("ecy:sfw")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:sfu:"))
async def economy_safe_upgrade(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = economy_sink_service.try_bank_safe_upgrade(char, floor_key=floor_key)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        await economy_sink_service.flush(session, char)
        await _refresh_bank_safe_screen(state, query, char, floor_key)
        await query.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("ecy:sfu")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:sfi:"))
async def economy_safe_claim_interest(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = economy_sink_service.try_claim_bank_interest(char, floor_key=floor_key)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        await economy_sink_service.flush(session, char)
        await _refresh_bank_safe_screen(state, query, char, floor_key)
        await query.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("ecy:sfi")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:sfs:"))
async def economy_safe_seal(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = economy_sink_service.try_unlock_bank_seal(char, floor_key=floor_key)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        await economy_sink_service.flush(session, char)
        await _refresh_bank_safe_screen(state, query, char, floor_key)
        await query.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("ecy:sfs")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:topn:"))
async def economy_term_open(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        term_h = int(parts[3])
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        bal = sink_rules.bank_safe_balance(char)
        if bal < 100:
            await query.answer("В сейфе должно быть минимум 100 💰 для срочного вклада.", show_alert=True)
            return
        amt = bal if bal < 200 else max(100, bal // 2)
        ok, msg = economy_sink_service.try_open_bank_term(
            char,
            floor_key=floor_key,
            amount=amt,
            term_h=term_h,
        )
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        await economy_sink_service.flush(session, char)
        await _refresh_bank_safe_screen(state, query, char, floor_key)
        await query.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("ecy:topn")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("ecy:tcl:"))
async def economy_term_close(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        force_early = bool(int(parts[3]))
        char = await _load_char_for_mutation(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = economy_sink_service.try_close_bank_term(
            char,
            floor_key=floor_key,
            force_early=force_early,
        )
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        await economy_sink_service.flush(session, char)
        await _refresh_bank_safe_screen(state, query, char, floor_key)
        await query.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("ecy:tcl")
        await query.answer("Ошибка.", show_alert=True)

