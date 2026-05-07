"""Арена: пошаговая дуэль, вызов по ID или ответу, меню."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, t
from bot.states.arena_states import ArenaChallengeStates, ArenaTurnStates
from bot.states.combat_states import CombatStates
from bot.utils.game_art import menu_arena_photo_path
from bot.utils.game_ui import edit_game_message_content, push_game_ui
from config import is_admin as config_is_admin
from db.models.character import Character
from db.repository import character_repo, user_repo
from services import arena_service
from services.fame_bonuses import max_arena_matches_per_day

router = Router(name="arena")


def _arena_turn_keyboard(*, is_phantom: bool = False) -> InlineKeyboardMarkup:
    back_cb = "arn:phantoms" if is_phantom else "mnu:arn"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚔️ Удар", callback_data="arn:mv:atk"),
                InlineKeyboardButton(text="🛡️ Защита", callback_data="arn:mv:def"),
            ],
            [InlineKeyboardButton(text="🏳️ Сдаться", callback_data="arn:mv:forfeit")],
            [InlineKeyboardButton(text="📋 Меню", callback_data=back_cb)],
        ],
    )


def _phantom_turn_keyboard() -> InlineKeyboardMarkup:
    return _arena_turn_keyboard(is_phantom=True)


def _parse_arena_target(
    message: Message,
    command: CommandObject,
) -> tuple[int | None, str | None, int | None, bool]:
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


async def _start_turn_duel_for_character(
    *,
    session: AsyncSession,
    state: FSMContext,
    char: Character,
    locale: str,
    fixed_opponent: Character | None,
    target_message: Message | None,
    reply_message: Message | None,
) -> None:
    opp, o_name, o_pow, banner, win_bonus, is_npc = await arena_service.prepare_arena_turn_opponent(
        session,
        char,
        fixed_opponent=fixed_opponent,
    )
    o_mmr = 1000
    if opp is not None:
        o_mmr = arena_service.arena_mmr(opp)
    else:
        o_mmr = max(650, 920 + int(char.floor_number) * 3)
    st = arena_service.build_turn_duel_open_state(
        character=char,
        opponent=opp,
        opponent_name=o_name,
        opponent_power=o_pow,
        opponent_mmr=o_mmr,
        banner_html=banner,
        win_bonus=win_bonus,
        is_npc=is_npc,
    )
    st["hist"] = []
    await state.set_state(ArenaTurnStates.in_duel)
    await state.update_data(arn_duel=st)
    body = arena_service.format_turn_duel_screen_html(st, log_lines=st["hist"])
    text = f"{t(locale, 'arena_title')}\n\n{body}"
    kb = _arena_turn_keyboard()
    if target_message is not None:
        await edit_game_message_content(
            target_message,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    elif reply_message is not None:
        await reply_message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )


async def _run_arena_turn_flow(
    *,
    message: Message | None,
    callback: CallbackQuery | None,
    session: AsyncSession,
    state: FSMContext,
    fixed_opponent: Character | None,
    command: CommandObject | None,
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

    from game.mercenaries.shadow_market_meta import arena_coliseum_block_message, party_blocks_arena_coliseum

    if not config_is_admin(uid) and party_blocks_arena_coliseum(char):
        msg = arena_coliseum_block_message()
        if callback:
            await callback.answer(msg, show_alert=True)
        elif message:
            await message.answer(msg)
        return

    if arena_service.arena_daily_limit_reached(char):
        msg = t(
            loc,
            "arena_daily_limit",
            limit=max_arena_matches_per_day(char),
        )
        if callback:
            await callback.answer(msg, show_alert=True)
        elif message:
            await message.answer(msg)
        return

    resolved_fixed: Character | None = fixed_opponent
    if message is not None and command is not None:
        tid, uname, digit_tok, need_help = _parse_arena_target(message, command)
        if need_help:
            await message.answer(t(loc, "arena_help"), parse_mode=ParseMode.HTML)
            return
        if digit_tok is not None:
            opp, err_key = await arena_service.resolve_opponent_digit_token(session, char, digit_tok)
            if err_key:
                await message.answer(t(loc, err_key), parse_mode=ParseMode.HTML)
                return
            resolved_fixed = opp
        elif tid is not None or (uname and uname.strip()):
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

    await _start_turn_duel_for_character(
        session=session,
        state=state,
        char=char,
        locale=loc,
        fixed_opponent=resolved_fixed,
        target_message=callback.message if callback else None,
        reply_message=message if message else None,
    )

    if callback:
        await callback.answer()
    await session.commit()


@router.message(Command("arena"))
async def cmd_arena(message: Message, session: AsyncSession, state: FSMContext, command: CommandObject) -> None:
    try:
        await _run_arena_turn_flow(
            message=message,
            callback=None,
            session=session,
            state=state,
            fixed_opponent=None,
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
        left = arena_service.arena_matches_remaining_today(char)
        intro = t(loc, "arena_menu_intro")
        limits = t(
            loc,
            "arena_menu_limits",
            limit=max_arena_matches_per_day(char),
            left=left,
        )
        spn = arena_service.spirit_arena_charges(char)
        spirit_line = (
            f"\n👻 Запасных боёв: <b>{spn}</b> <i>(события этажа, сверх дневного лимита)</i>"
            if spn
            else ""
        )
        mmr = arena_service.arena_mmr(char)
        league = arena_service.arena_league_label(mmr)
        mmr_line = f"\n📊 MMR: <b>{mmr}</b> · {league} <i>(сезон {arena_service.ARENA_SEASON_ID})</i>"
        my_id = char.game_id
        id_hint = (
            t(loc, "arena_your_game_id", gid=my_id)
            if my_id is not None
            else t(loc, "arena_no_game_id_yet")
        )
        duel_hint = (
            "<i>Пошаговый бой: удар или защита кнопками. Вызов соперника — числом в чат после кнопки ниже "
            "или команда <code>/arena N</code> (игровой ID или Telegram ID).</i>"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(loc, "arena_random_btn"),
                        callback_data="arn:rand",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="⚔️ Вызов по игровому ID (ПвП)",
                        callback_data="arn:wait",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="👻 Фантомы Топ-10 (тренировка)",
                        callback_data="arn:phantoms",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=t(loc, "arena_back_btn"),
                        callback_data="mnu:hub",
                    ),
                ],
            ],
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"{intro}\n\n{id_hint}\n\n{limits}{spirit_line}{mmr_line}\n\n{duel_hint}",
            reply_markup=kb,
            target_message=callback.message,
            photo_path=menu_arena_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("mnu:arn")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "arn:wait")
async def arena_wait_opponent_id(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t("ru", "arena_busy"), show_alert=True)
            return
        await state.clear()
        await state.set_state(ArenaChallengeStates.waiting_opponent_token)
        await edit_game_message_content(callback.message,
            "✏️ <b>Вызов по ID</b>\n"
            "Отправь в этот чат <b>одно число</b> — игровой ID героя из «Статус» соперника "
            "или его Telegram ID (если знаешь).\n"
            "<i>Отмена — команда /start или кнопка «Арена» в меню снова.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ В меню арены", callback_data="mnu:arn")],
                ],
            ),
        )
        await callback.answer()
    except Exception:
        logger.exception("arn:wait")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(StateFilter(ArenaChallengeStates.waiting_opponent_token), F.text)
async def arena_opponent_id_message(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await state.clear()
            await message.answer("Сначала заверши бой.")
            return
        raw = (message.text or "").strip().replace(" ", "").replace("\u00a0", "")
        if not raw.isdigit():
            await message.answer("Нужно одно целое число — игровой ID или Telegram ID.")
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            await state.clear()
            await message.answer("Нет доступа.")
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await state.clear()
            await message.answer("Сначала /start.")
            return
        loc = get_locale(char, message.from_user.language_code)
        if arena_service.arena_daily_limit_reached(char):
            await state.clear()
            await message.answer(
                t(loc, "arena_daily_limit", limit=max_arena_matches_per_day(char)),
            )
            return
        from game.mercenaries.shadow_market_meta import arena_coliseum_block_message, party_blocks_arena_coliseum

        if not config_is_admin(message.from_user.id) and party_blocks_arena_coliseum(char):
            await state.clear()
            await message.answer(arena_coliseum_block_message(), parse_mode=ParseMode.HTML)
            return
        tok = int(raw)
        opp, err_key = await arena_service.resolve_opponent_digit_token(session, char, tok)
        if err_key:
            await message.answer(t(loc, err_key), parse_mode=ParseMode.HTML)
            return
        await state.clear()
        await _start_turn_duel_for_character(
            session=session,
            state=state,
            char=char,
            locale=loc,
            fixed_opponent=opp,
            target_message=None,
            reply_message=message,
        )
        await session.commit()
    except Exception:
        logger.exception("arena_opponent_id_message")
        await state.clear()
        await message.answer("Ошибка арены.")


@router.callback_query(F.data == "arn:rand")
async def arena_random_duel(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _run_arena_turn_flow(
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


@router.callback_query(F.data == "arn:phantoms")
async def arena_phantoms_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Список фантомов Топ-10 — выбор соперника для тренировочного боя."""
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
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
            await callback.answer("Сначала создай героя.", show_alert=True)
            return

        phantoms = await arena_service.top10_phantoms(session, char.id)
        if not phantoms:
            await callback.answer("Пока нет других игроков в базе.", show_alert=True)
            return

        lines = ["👻 <b>Фантомы Топ-10</b> — тренировочные бои без наград\n"]
        rows: list[list[InlineKeyboardButton]] = []
        for i, (phchar, pow_, name) in enumerate(phantoms, 1):
            gid = int(phchar.game_id) if phchar.game_id is not None else 0
            lines.append(
                f"<b>{i}.</b> {name} · 🏰 эт.{phchar.floor_number} · ⭐lv.{phchar.level} · 💪{int(pow_)}"
            )
            rows.append([
                InlineKeyboardButton(
                    text=f"⚔️ #{i} {name[:20]} (lv.{phchar.level})",
                    callback_data=f"arn:phantom:{phchar.id}",
                )
            ])
        rows.append([InlineKeyboardButton(text="⬅️ Арена", callback_data="mnu:arn")])
        rows.append([InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")])

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            target_message=callback.message,
            photo_path=menu_arena_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("arn:phantoms")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("arn:phantom:"))
async def arena_phantom_fight(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Начать тренировочный бой с фантомом (без наград, без учёта лимита)."""
    try:
        if callback.from_user is None or callback.message is None or callback.data is None or callback.bot is None:
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
            await callback.answer("Сначала создай героя.", show_alert=True)
            return

        from game.mercenaries.shadow_market_meta import arena_coliseum_block_message, party_blocks_arena_coliseum

        if not config_is_admin(callback.from_user.id) and party_blocks_arena_coliseum(char):
            await callback.answer(arena_coliseum_block_message(), show_alert=True)
            return

        raw_id = callback.data.split(":")[-1]
        if not raw_id.isdigit():
            await callback.answer("Неверный ID.", show_alert=True)
            return
        phantom_char = await character_repo.get_by_id(session, int(raw_id))
        if phantom_char is None or int(phantom_char.id) == int(char.id):
            await callback.answer("Фантом не найден.", show_alert=True)
            return

        loc = get_locale(char, callback.from_user.language_code)
        _, st = await arena_service.prepare_phantom_fight(session, char, phantom_char)
        await state.set_state(ArenaTurnStates.in_duel)
        await state.update_data(arn_duel=st)
        body = arena_service.format_turn_duel_screen_html(st, log_lines=[])
        text = f"👻 <b>Тренировочный бой</b>\n\n{body}"
        await edit_game_message_content(callback.message,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=_phantom_turn_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("arn:phantom")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("arn:mv:"))
async def arena_turn_move(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.data is None:
            await callback.answer()
            return
        if await state.get_state() != ArenaTurnStates.in_duel.state:
            await callback.answer("Нет активного боя.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет героя.", show_alert=True)
            return
        data = await state.get_data()
        raw = data.get("arn_duel")
        if not isinstance(raw, dict):
            await callback.answer("Сессия устарела.", show_alert=True)
            await state.clear()
            return
        move = (callback.data.split(":")[-1] or "atk").lower()
        if move == "forfeit":
            st = dict(raw)
            st["hist"] = list(st.get("hist", [])) + ["🏳️ Ты сдался."]
            st["p_hp"] = 0
            outcome = "lose"
        else:
            base = dict(raw)
            prev_hist = list(base.pop("hist", []))
            st, step_logs, outcome = arena_service.apply_turn_duel_step(char, base, move)
            st["hist"] = prev_hist + step_logs

        loc = get_locale(char, callback.from_user.language_code)

        is_phantom = bool(st.get("is_phantom"))
        kb_now = _phantom_turn_keyboard() if is_phantom else _arena_turn_keyboard()

        if outcome is None:
            await state.update_data(arn_duel=st)
            body = arena_service.format_turn_duel_screen_html(st, log_lines=st.get("hist"))
            title = "👻 <b>Тренировочный бой</b>" if is_phantom else t(loc, "arena_title")
            text = f"{title}\n\n{body}"
            await edit_game_message_content(callback.message,
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb_now,
            )
            await callback.answer()
            await session.commit()
            return

        await state.clear()
        body = arena_service.format_turn_duel_screen_html(st, log_lines=st.get("hist"))

        if is_phantom:
            # Тренировка — без награды, без лимита
            footer = arena_service.finish_phantom_duel_no_economy(st)
            back_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👻 Топ-10 фантомов", callback_data="arn:phantoms")],
                [InlineKeyboardButton(text="🏟️ Арена", callback_data="mnu:arn")],
                [InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")],
            ])
            full = f"👻 <b>Тренировочный бой</b>\n\n{body}\n\n{footer}"
            await edit_game_message_content(callback.message,full, parse_mode=ParseMode.HTML, reply_markup=back_kb)
            await callback.answer()
            await session.commit()
            return

        rep, gold_delta, out = arena_service.finish_turn_duel_economy(
            char,
            outcome=outcome,
            is_npc=bool(st.get("is_npc")),
            win_bonus=int(st.get("win_bonus") or 0),
            opponent_mmr=int(st.get("o_mmr", 1000) or 1000),
        )
        header = t(loc, "arena_title")
        if out == "win":
            footer = t(loc, "arena_result_win", gold=gold_delta)
        elif out == "lose":
            if gold_delta < 0:
                footer = t(loc, "arena_result_lose_penalty", gold=abs(gold_delta))
            else:
                footer = t(loc, "arena_result_lose_no_gold")
        else:
            footer = t(loc, "arena_draw")
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏟️ Арена", callback_data="mnu:arn")],
            [InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")],
        ])
        full = f"{header}\n\n{body}\n\n{rep}\n\n{footer}"
        await edit_game_message_content(callback.message,full, parse_mode=ParseMode.HTML, reply_markup=back_kb)
        await callback.answer()
        await session.commit()
    except Exception:
        logger.exception("arn:mv")
        await callback.answer("Ошибка.", show_alert=True)
