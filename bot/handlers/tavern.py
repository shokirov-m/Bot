"""
Таверна в городах: меню, покупка еды и ночлега (колбэки tvr:*).
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.tavern_kb import buyer_quest_keyboard, tavern_daily_keyboard, tavern_menu_keyboard
from bot.utils.game_art import menu_city_photo_path
from bot.utils.game_ui import edit_game_message_content, push_game_ui
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
async def tavern_open(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=tavern_menu_keyboard(char.floor_number),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("tvr:open")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("tvr:buy:"))
async def tavern_buy(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=f"{header}\n\n{LINE_SEP}\n{payload}",
            reply_markup=tavern_menu_keyboard(char.floor_number),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer("Приятного!")
    except Exception:
        logger.exception("tvr:buy")
        await query.answer("Ошибка.", show_alert=True)


# ── Скупщик Орин ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^tvr:buyer:\d+$"))
async def tavern_buyer_open(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Открыть экран Скупщика Орина."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не в этом городе.", show_alert=True)
            return
        from services import tavern_buyer_service as bqs
        text = bqs.format_buyer_quest_html(char, floor_key)
        state = bqs._get_state(char, floor_key)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=buyer_quest_keyboard(floor_key, state),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("tvr:buyer")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^tvr:bq:start:\d+$"))
async def tavern_buyer_start(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[3])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не в этом городе.", show_alert=True)
            return
        from services import tavern_buyer_service as bqs
        ok = bqs.start_chain(char, floor_key)
        if not ok:
            await query.answer("Цепочка уже начата или недоступна.", show_alert=True)
            return
        await session.flush()
        text = bqs.format_buyer_quest_html(char, floor_key)
        state = bqs._get_state(char, floor_key)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=buyer_quest_keyboard(floor_key, state),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer("🪙 Поручения приняты!")
    except Exception:
        logger.exception("tvr:bq:start")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^tvr:bq:claim:\d+:\d+$"))
async def tavern_buyer_claim_step(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[3])
        step = int(parts[4])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не в этом городе.", show_alert=True)
            return
        from services import tavern_buyer_service as bqs
        ok, msg = await bqs.claim_step(session, char, floor_key, step)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        # Читаем state ДО commit, пока char не сброшен
        text = bqs.format_buyer_quest_html(char, floor_key)
        state = bqs._get_state(char, floor_key)
        await session.commit()
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=f"{text}\n\n{msg}",
            reply_markup=buyer_quest_keyboard(floor_key, state),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer("✅ Шаг выполнен!")
    except Exception:
        logger.exception("tvr:bq:claim")
        await query.answer("Ошибка.", show_alert=True)


# ── Дневная ротация: чертежи и снаряжение ────────────────────────────────────


async def _render_tavern_daily(state: FSMContext, query: CallbackQuery, char) -> None:
    text = tavern_service.format_tavern_daily_html(char)
    offers = tavern_service.daily_offers_for_character(char)
    state = tavern_service._tavern_daily_state(char)
    bb = set(state.get("bought_blueprints") or [])
    bg = set(state.get("bought_gears") or [])
    known = set(tavern_service.known_recipes(char))
    if query.message is not None:
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=tavern_daily_keyboard(int(char.floor_number), offers, bb, bg, known),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )


@router.callback_query(F.data.regexp(r"^tvr:daily:\d+$"))
async def tavern_daily_open(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не в этом городе.", show_alert=True)
            return
        if not tavern_loc.tavern_available_on_floor(char.floor_number):
            await query.answer("Здесь нет таверны.", show_alert=True)
            return
        await _render_tavern_daily(state, query, char)
        await query.answer()
    except Exception:
        logger.exception("tvr:daily:open")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^tvr:daily:\d+:nop$"))
async def tavern_daily_nop(query: CallbackQuery) -> None:
    await query.answer()


@router.callback_query(F.data.regexp(r"^tvr:daily:bp:\d+:[A-Za-z0-9_]+$"))
async def tavern_daily_buy_blueprint(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[3])
        recipe_id = parts[4]
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не в этом городе.", show_alert=True)
            return
        ok, msg = await tavern_service.try_buy_daily_blueprint(session, char, recipe_id)
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        await session.commit()
        await _render_tavern_daily(query, char)
        await query.answer("Куплено!")
    except Exception:
        logger.exception("tvr:daily:bp")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^tvr:daily:gr:\d+:[A-Za-z0-9_]+$"))
async def tavern_daily_buy_gear(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[3])
        gear_key = parts[4]
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не в этом городе.", show_alert=True)
            return
        ok, msg = await tavern_service.try_buy_daily_gear(session, char, gear_key)
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        await session.commit()
        await _render_tavern_daily(query, char)
        await query.answer("Куплено!")
    except Exception:
        logger.exception("tvr:daily:gr")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^tvr:bq:final:\d+$"))
async def tavern_buyer_final(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[3])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не в этом городе.", show_alert=True)
            return
        from services import tavern_buyer_service as bqs
        ok, msg = await bqs.claim_final_reward(session, char, floor_key)
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        # Читаем state ДО commit
        state = bqs._get_state(char, floor_key)
        await session.commit()
        await edit_game_message_content(query.message,
            msg,
            reply_markup=buyer_quest_keyboard(floor_key, state),
            parse_mode="HTML",
        )
        await query.answer("🏆 Цепочка завершена!")
    except Exception:
        logger.exception("tvr:bq:final")
        await query.answer("Ошибка.", show_alert=True)
