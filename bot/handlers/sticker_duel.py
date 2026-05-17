"""
Карточная арена башни: гача монстров 1–20 этажа, альбом, дуэли, ТОП. Меню Локации → Стикер-арена (mnu:stk).
Команды: /collection, /stickerpull, /stickerdueltop, /stickerleaderboard, /duel, /duel_accept <код>,
/towercard и /stickercard (превью карты в чат — тот же 12 ч кулдаун, что и у крутки; в альбом не пишет), /stickerhelp.
"""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, LabeledPrice, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.menu import _char_or_alert
from bot.i18n import get_locale, t
from bot.keyboards.sticker_duel_kb import defender_pick_keyboard, sticker_hub_keyboard, sticker_pick_keyboard
from bot.states.combat_states import CombatStates
from config import is_admin, settings
from db.models.character import Character
from db.repository import character_repo, sticker_duel_challenge_repo, user_repo
import services.combat.arena_service as arena_service
import services.social.sticker_duel_service as sticker_duel_service
import services.progression.unlock_service as unlock_service
from game.tower_cards import monster_cards as tc


class StickerDuelStates(StatesGroup):
    waiting_opponent_game_id = State()


router = Router(name="sticker_duel")


def _hub_html(char, loc: str = "ru") -> str:
    loc = "ru"
    free_left = max(0, sticker_duel_service.free_spin_cap(char) - sticker_duel_service.free_spins_used_today(char))
    paid_left = max(0, 20 - sticker_duel_service.paid_spins_used_today(char))
    stars = int(getattr(settings, "STICKER_GACHA_STARS_PULL", 0) or 0)
    stars_ln = (t(loc, "sticker_arena_stars_line", stars=stars) + "\n") if stars > 0 else ""
    return (
        t(loc, "sticker_arena_title")
        + "\n"
        + t(loc, "sticker_arena_subtitle")
        + "\n"
        + t(loc, "sticker_arena_free_left", n=free_left)
        + "\n"
        + t(loc, "sticker_arena_paid_left", n=paid_left, gold=int(settings.STICKER_GACHA_GOLD_PULL))
        + "\n"
        + stars_ln
        + "\n\n"
        + sticker_duel_service.profile_sticker_lines_html(char)
        + "\n\n<i>Превью карты (этажи 1–20): <code>/towercard</code>, "
        "<code>/stickercard</code>, <code>/стикер</code> или кнопка «Превью» — "
        "<b>тот же 12 ч перерыв</b>, что и у крутки; в альбом только крутка. "
        "Полная карточка уходит в <b>канал объявлений гачи</b> (как зеркало крутки). "
        "<code>/stickerhelp</code> — правила.</i>"
    )


async def _run_towercard_preview(
    session: AsyncSession,
    *,
    bot,
    chat_id: int,
    char: Character,
    state: FSMContext | None,
    loc: str,
) -> tuple[bool, str]:
    """Превью карты: не в альбом; общий кулдаун с круткой. Текст и картинка — в GACHA_BROADCAST_CHAT, как зеркало гачи."""
    wait = sticker_duel_service.card_reveal_seconds_until_available(char)
    if wait > 0:
        return False, sticker_duel_service.card_reveal_cooldown_notice_html(wait)
    if state is not None:
        if await state.get_state() == CombatStates.in_battle.state:
            return False, f"⚠️ {html.escape(t(loc, 'sticker_combat_busy'))}"
    await character_repo.lock_character_row(session, char.id)
    try:
        fl, spawn = tc.pick_random_spawn_f1_20()
        sid = spawn.template.key
        cap = tc.format_monster_card_spawn_html(spawn, fl, description_max_len=360)
        if len(cap) > 1020:
            cap = cap[:1000] + "\n…"
        p = tc.portrait_path(sid, fl)
        u = await user_repo.get_by_id(session, int(char.user_id))
        who = html.escape((char.display_name or "?").strip() or "?")
        if u is not None and (u.username or "").strip():
            who += f" (@{html.escape((u.username or '').strip())})"
        header = f"🎴 <b>Превью карты</b> · {who}\n<i>Не в альбом · /towercard</i>\n\n"
        full = header + cap
        posted = False
        if getattr(settings, "STICKER_MIRROR_TO_GACHA_CHAT", True):
            import services.social.gacha_broadcast_service as gacha_broadcast_service

            posted = await gacha_broadcast_service.broadcast_sticker_pack_activity(
                bot,
                session,
                html_text=full,
                sticker_file_ids=(),
                image_paths=(str(p),) if p is not None and p.is_file() else (),
            )
        if not posted:
            if p is not None and p.is_file():
                await bot.send_photo(chat_id, FSInputFile(p), caption=full, parse_mode=ParseMode.HTML)
            else:
                await bot.send_message(chat_id, full, parse_mode=ParseMode.HTML)
        ack = t(loc, "sticker_tc_sent_broadcast") if posted else t(loc, "sticker_tc_sent_here")
        try:
            await bot.send_message(chat_id, ack, parse_mode=ParseMode.HTML)
        except Exception:
            logger.debug("towercard ack to origin chat failed")
        sticker_duel_service.record_card_reveal(char)
        await session.commit()
        return True, ""
    except Exception as e:
        await session.rollback()
        logger.exception("towercard_preview")
        return False, f"Не удалось отправить карту: <code>{html.escape(str(e))}</code>"


def _parse_sticker_duel_target(message: Message) -> tuple[int | None, str | None, int | None]:
    """Reply → telegram_id; иначе первый токен: число или @username."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id, None, None
    raw = (message.text or "").strip()
    if not raw:
        return None, None, None
    tok = raw.split()[0].strip().lstrip("@")
    if tok.isdigit():
        return None, None, int(tok)
    return None, tok, None


async def _format_sticker_leaderboard_html(
    session: AsyncSession,
    char: Character,
    loc: str,
) -> str:
    rows = await character_repo.list_sticker_duel_leaderboard(session, limit=10)
    rank_self = await character_repo.sticker_duel_rank_for_character(session, char)
    lines = [t(loc, "sticker_top_title"), ""]
    for i, (_cid, name, _gid, rating, wins, losses, uname) in enumerate(rows, start=1):
        un = f"@{html.escape(uname)}" if uname else html.escape(name)
        lines.append(t(loc, "sticker_top_line", i=i, who=un, rating=int(rating), wins=int(wins)))
    lines.append("")
    lines.append(t(loc, "sticker_top_self", rating=int(char.sticker_duel_rating), place=int(rank_self)))
    return "\n".join(lines)


@router.callback_query(F.data == "mnu:stk")
async def sticker_menu_open(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await state.clear()
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        if not unlock_service.is_unlocked(char, "menu_sticker"):
            await callback.answer(
                t(
                    loc,
                    "sticker_unlock_alert",
                    level=unlock_service.UNLOCK_BY_KEY["menu_sticker"].level,
                ),
                show_alert=True,
            )
            return
        from utils.telegram.game_ui import push_game_ui
        from utils.media.game_art import menu_locations_photo_path

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_hub_html(char, loc),
            reply_markup=sticker_hub_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=menu_locations_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("mnu:stk")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stk:alb")
async def sticker_album_cb(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        from utils.telegram.game_ui import push_game_ui
        from utils.media.game_art import menu_locations_photo_path

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=sticker_duel_service.format_collection_screen_html(char),
            reply_markup=sticker_hub_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=menu_locations_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stk:alb")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stk:top")
async def sticker_top_cb(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        text = await _format_sticker_leaderboard_html(session, char, loc)
        from utils.telegram.game_ui import push_game_ui
        from utils.media.game_art import menu_locations_photo_path

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=sticker_hub_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=menu_locations_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stk:top")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stk:sp:f")
async def sticker_spin_free(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        if not unlock_service.is_unlocked(char, "menu_sticker"):
            await callback.answer(
                t(
                    loc,
                    "sticker_unlock_alert",
                    level=unlock_service.UNLOCK_BY_KEY["menu_sticker"].level,
                ),
                show_alert=True,
            )
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t(loc, "sticker_combat_busy"), show_alert=True)
            return
        await character_repo.lock_character_row(session, char.id)
        ok, msg, sid, src_floor = sticker_duel_service.perform_spin(char, paid=False)
        await session.commit()
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await sticker_duel_service.send_card_art_after_pull(callback.bot, callback.message.chat.id, sid, src_floor)
        await sticker_duel_service.mirror_sticker_spin_to_gacha_chat(
            callback.bot,
            session,
            char,
            msg_html=msg,
            sticker_id=sid,
        )
        from utils.telegram.game_ui import push_game_ui
        from utils.media.game_art import menu_locations_photo_path

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_hub_html(char, loc) + "\n\n" + msg,
            reply_markup=sticker_hub_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=menu_locations_photo_path(),
            character=char,
        )
        await callback.answer(t(loc, "sticker_spin_free_ok"))
    except Exception:
        logger.exception("stk:sp:f")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stk:sp:p")
async def sticker_spin_paid(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        if not unlock_service.is_unlocked(char, "menu_sticker"):
            await callback.answer(
                t(
                    loc,
                    "sticker_unlock_alert",
                    level=unlock_service.UNLOCK_BY_KEY["menu_sticker"].level,
                ),
                show_alert=True,
            )
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t(loc, "sticker_combat_busy"), show_alert=True)
            return
        await character_repo.lock_character_row(session, char.id)
        ok, msg, sid, src_floor = await sticker_duel_service.apply_paid_spin_gold(session, char)
        await session.commit()
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await sticker_duel_service.send_card_art_after_pull(callback.bot, callback.message.chat.id, sid, src_floor)
        await sticker_duel_service.mirror_sticker_spin_to_gacha_chat(
            callback.bot,
            session,
            char,
            msg_html=msg,
            sticker_id=sid,
        )
        from utils.telegram.game_ui import push_game_ui
        from utils.media.game_art import menu_locations_photo_path

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_hub_html(char, loc) + "\n\n" + msg,
            reply_markup=sticker_hub_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=menu_locations_photo_path(),
            character=char,
        )
        await callback.answer(t(loc, "sticker_spin_paid_ok"))
    except Exception:
        logger.exception("stk:sp:p")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stk:sp:s")
async def sticker_spin_stars_invoice(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        price = int(getattr(settings, "STICKER_GACHA_STARS_PULL", 0) or 0)
        if price <= 0:
            loc0 = get_locale(None, callback.from_user.language_code if callback.from_user else None)
            await callback.answer(t(loc0, "sticker_stars_disabled"), show_alert=True)
            return
        if callback.message is None or callback.bot is None or callback.from_user is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        loc = get_locale(char, callback.from_user.language_code)
        if not unlock_service.is_unlocked(char, "menu_sticker"):
            await callback.answer(
                t(
                    loc,
                    "sticker_unlock_alert",
                    level=unlock_service.UNLOCK_BY_KEY["menu_sticker"].level,
                ),
                show_alert=True,
            )
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t(loc, "sticker_combat_busy"), show_alert=True)
            return
        payload = f"stickerspin:{callback.from_user.id}"
        await callback.bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=t(loc, "sticker_invoice_title"),
            description=t(loc, "sticker_invoice_desc"),
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label=t(loc, "sticker_invoice_label"), amount=price)],
        )
        await callback.answer()
    except Exception:
        logger.exception("stk:sp:s")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stk:duel")
async def sticker_duel_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        if not unlock_service.is_unlocked(char, "menu_sticker"):
            await callback.answer(
                t(
                    loc,
                    "sticker_unlock_alert",
                    level=unlock_service.UNLOCK_BY_KEY["menu_sticker"].level,
                ),
                show_alert=True,
            )
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer(t(loc, "sticker_combat_busy"), show_alert=True)
            return
        kb = sticker_pick_keyboard(character=char, locale=loc)
        if kb is None:
            await callback.answer(t(loc, "sticker_no_stickers_for_duel"), show_alert=True)
            return
        await state.set_state(StickerDuelStates.waiting_opponent_game_id)
        await state.update_data(stk_atk_sid=None)
        from utils.telegram.game_ui import push_game_ui
        from utils.media.game_art import menu_locations_photo_path

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=t(loc, "sticker_duel_start_prompt"),
            reply_markup=kb,
            target_message=callback.message,
            photo_path=menu_locations_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("stk:duel")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("stk:at:"))
async def sticker_duel_pick_attacker_card(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        sid = (callback.data or "").split(":", 2)[2]
        if callback.message is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        if sid not in sticker_duel_service.collection_map(char):
            await callback.answer(t(loc, "sticker_duel_invalid_card"), show_alert=True)
            return
        await state.update_data(stk_atk_sid=sid)
        await callback.answer(t(loc, "sticker_duel_pick_card_hint"))
        await callback.message.answer(
            t(loc, "sticker_duel_enter_target"),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("stk:at")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(Command("collection"))
async def cmd_collection(message: Message, session: AsyncSession) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Сначала /start.")
            return
        await message.answer(
            sticker_duel_service.format_collection_screen_html(char),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("collection")


@router.message(Command("stickerdueltop"))
async def cmd_sticker_top(message: Message, session: AsyncSession) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Сначала /start.")
            return
        loc = get_locale(char, message.from_user.language_code)
        text = await _format_sticker_leaderboard_html(session, char, loc)
        await message.answer(text, parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("stickerdueltop")


@router.message(Command("stickerleaderboard"))
async def cmd_sticker_leaderboard(message: Message, session: AsyncSession) -> None:
    await cmd_sticker_top(message, session)


@router.message(Command("stickerpull"))
async def cmd_stickerpull(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        await state.clear()
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Сначала /start.")
            return
        loc = get_locale(char, message.from_user.language_code)
        if not unlock_service.is_unlocked(char, "menu_sticker"):
            await message.answer(
                t(loc, "sticker_unlock_alert", level=unlock_service.UNLOCK_BY_KEY["menu_sticker"].level),
            )
            return
        await message.answer(
            _hub_html(char, loc),
            parse_mode=ParseMode.HTML,
            reply_markup=sticker_hub_keyboard(locale=loc),
        )
    except Exception:
        logger.exception("stickerpull")


@router.message(Command("duel"))
async def cmd_duel(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Точка входа в карточную дуэль (как кнопка «Вызвать на дуэль»)."""
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Сначала /start.")
            return
        loc = get_locale(char, message.from_user.language_code)
        if not unlock_service.is_unlocked(char, "menu_sticker"):
            await message.answer(
                t(loc, "sticker_unlock_alert", level=unlock_service.UNLOCK_BY_KEY["menu_sticker"].level),
            )
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await message.answer(t(loc, "sticker_combat_busy"))
            return
        kb = sticker_pick_keyboard(character=char, locale=loc)
        if kb is None:
            await message.answer(t(loc, "sticker_no_stickers_for_duel"))
            return
        await state.set_state(StickerDuelStates.waiting_opponent_game_id)
        await state.update_data(stk_atk_sid=None)
        await message.answer(t(loc, "sticker_duel_start_prompt"), parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception:
        logger.exception("cmd_duel")
        await message.answer("Ошибка.")


@router.message(Command("duel_accept"))
async def cmd_duel_accept(message: Message, session: AsyncSession, command: CommandObject) -> None:
    try:
        if message.from_user is None:
            return
        code = (command.args or "").strip().split()[0] if command.args else ""
        if not code:
            loc = get_locale(None, message.from_user.language_code)
            await message.answer(t(loc, "sticker_duel_accept_usage"), parse_mode=ParseMode.HTML)
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Сначала /start.")
            return
        loc = get_locale(char, message.from_user.language_code)
        kb = defender_pick_keyboard(code.upper(), char, locale=loc)
        if kb is None:
            await message.answer(t(loc, "sticker_duel_no_cards_defend"))
            return
        await message.answer(
            t(loc, "sticker_duel_pick_defender", code=html.escape(code.upper())),
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    except Exception:
        logger.exception("duel_accept")


@router.message(StateFilter(StickerDuelStates.waiting_opponent_game_id))
async def sticker_duel_opponent_entered(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            return
        loc = get_locale(char, message.from_user.language_code)
        data = await state.get_data()
        sid = str(data.get("stk_atk_sid") or "")
        if not sid:
            await state.clear()
            await message.answer(t(loc, "sticker_duel_session_reset"))
            return
        tid, uname, num_tok = _parse_sticker_duel_target(message)
        if num_tok is not None:
            opp, err_key = await arena_service.resolve_opponent_digit_token(session, char, num_tok)
        elif tid is not None or (uname and uname.strip()):
            opp, err_key = await arena_service.resolve_opponent(
                session,
                char,
                telegram_id=tid,
                username=uname,
            )
        else:
            await message.answer(t(loc, "sticker_duel_need_target"))
            return
        if err_key:
            await message.answer(t(loc, err_key), parse_mode=ParseMode.HTML)
            return
        a, b = sorted([int(char.id), int(opp.id)])
        await character_repo.lock_character_row(session, a)
        await character_repo.lock_character_row(session, b)
        ok, msg, code = await sticker_duel_service.create_duel_challenge(
            session,
            attacker=char,
            defender=opp,
            attacker_sticker_id=sid,
        )
        await session.commit()
        await state.clear()
        if not ok:
            await message.answer(msg)
            return
        code_esc = html.escape(code or "")
        await message.answer(
            msg + "\n\n" + t(loc, "sticker_duel_waiting"),
            parse_mode=ParseMode.HTML,
        )
        du = await user_repo.get_by_id(session, int(opp.user_id))
        if du is not None and message.bot is not None:
            loc_def = get_locale(opp, None)
            try:
                await message.bot.send_message(
                    du.telegram_id,
                    t(loc_def, "sticker_challenged_notify", code=code_esc),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                logger.debug("sticker duel notify defender failed")
    except Exception:
        logger.exception("sticker_duel_opponent")
        await message.answer("Ошибка.")


@router.callback_query(F.data.startswith("stk:ac:"))
async def sticker_duel_defender_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        parts = (callback.data or "").split(":")
        # stk:ac:CODE:sid
        if len(parts) < 4:
            await callback.answer()
            return
        code = parts[2]
        sid = parts[3]
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer()
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer()
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        ch = await sticker_duel_challenge_repo.fetch_challenge(session, code)
        if ch is None:
            await callback.answer(t(loc, "sticker_challenge_not_found"), show_alert=True)
            return
        atk_sid = str(ch["attacker_sticker_id"])
        aid = int(ch["attacker_character_id"])
        first, second = sorted([int(char.id), aid])
        await character_repo.lock_character_row(session, first)
        await character_repo.lock_character_row(session, second)
        attacker = await character_repo.get_by_id(session, aid)
        ok, result_html = await sticker_duel_service.resolve_duel_by_code(
            session,
            defender=char,
            code=code,
            defender_sticker_id=sid,
        )
        await session.commit()
        if not ok:
            await callback.answer(result_html, show_alert=True)
            return
        hdr = (
            "⚔️ <b>Карточная дуэль</b>\n"
            f"<i>{html.escape((attacker.display_name or '?').strip() if attacker else '?')}</i> vs "
            f"<i>{html.escape((char.display_name or '?').strip())}</i>"
        )
        await sticker_duel_service.mirror_sticker_duel_to_gacha_chat(
            callback.bot,
            session,
            header_html=hdr,
            result_html=result_html,
            attacker_sticker_id=atk_sid,
            defender_sticker_id=sid,
            attacker=attacker,
            defender=char,
        )
        await callback.answer("Бой!")
        await callback.message.answer(result_html, parse_mode=ParseMode.HTML)
        if attacker is not None:
            au = await user_repo.get_by_id(session, int(attacker.user_id))
            if au is not None:
                try:
                    await callback.bot.send_message(
                        int(au.telegram_id),
                        "⚔️ <b>Результат карточной дуэли</b>\n" + result_html,
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    logger.debug("notify attacker duel result failed")
    except Exception:
        logger.exception("stk:ac")
        await callback.answer("Ошибка.", show_alert=True)


STICKER_MECHANICS_HTML = (
    "📖 <b>Карточная арена башни</b>\n\n"
    "<b>1. Коллекция</b>\n"
    "Карты — монстры с <b>этажей 1–20</b>. В мета-прогрессе хранятся ключ шаблона, "
    "<b>имя</b>, <b>редкость</b> (звёздность), <b>стихия для дуэли</b> (огонь, вода, земля), "
    "<b>атака</b> и <b>защита</b> (масштаб от этажа выпадения).\n\n"
    "<b>2. Атака и защита</b>\n"
    "Берутся из каталога монстров башни и умножаются на коэффициент этажа. "
    "При дубликате той же карты к атаке добавляется <b>+2</b>.\n\n"
    "<b>3. Перерыв 12 часов</b>\n"
    "После <b>любой крутки гачи</b> или после <b>превью карты</b> "
    "(<code>/towercard</code>, <code>/stickercard</code>, <code>/стикер</code>, кнопка «Превью» в меню арены) "
    "следующее раскрытие карты (снова крутка <i>или</i> превью) доступно не раньше чем через <b>12 часов</b>. "
    "Так превью не обходит экономику карт.\n\n"
    "<b>4. Дуэль</b>\n"
    "Игроки выбирают карты из коллекции; победитель считается по стихиям (камень-ножницы-бумага) "
    "и при ничьей по сумме атаки и защиты.\n\n"
    "<b>5. Превью в чате</b>\n"
    "Команды <code>/towercard</code>, <code>/stickercard</code>, <code>/стикер</code> или кнопка "
    "«Превью карты»: полная карточка уходит в <b>тот же канал</b>, что и зеркало крутки гачи "
    "(<code>GACHA_BROADCAST_CHAT</code> и доп. чаты из payload), если зеркало включено; иначе превью только в чате, "
    "где вызвали команду. В альбом карта не попадает. С круткой общий перерыв 12 ч (см. п. 3).\n\n"
    "<b>Админ</b>: <code>/admin_sticker_set имя_набора</code> — список стикеров Telegram (если нужен для других целей)."
)


@router.callback_query(F.data == "stk:tc:i")
async def sticker_preview_info_cb(callback: CallbackQuery) -> None:
    loc = "ru"
    try:
        await callback.answer(t(loc, "sticker_preview_rules_alert"), show_alert=True)
    except Exception:
        logger.exception("stk:tc:i")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "stk:tc")
async def sticker_preview_from_hub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        _, char = await _char_or_alert(session, callback)
        if char is None:
            await callback.answer()
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        if not unlock_service.is_unlocked(char, "menu_sticker"):
            await callback.answer(
                t(loc, "sticker_unlock_alert", level=unlock_service.UNLOCK_BY_KEY["menu_sticker"].level),
                show_alert=True,
            )
            return
        ok, err = await _run_towercard_preview(
            session,
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            char=char,
            state=state,
            loc=loc,
        )
        if not ok:
            await callback.message.answer(err, parse_mode=ParseMode.HTML)
            await callback.answer(t(loc, "sticker_tc_blocked"))
            return
        await callback.answer(t(loc, "sticker_tc_ok"))
    except Exception:
        logger.exception("stk:tc")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(Command("towercard", "stickercard", "sticker_card", "стикер"))
async def cmd_stickercard(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Превью карты: тот же кулдаун, что у крутки; в альбом не пишет."""
    try:
        if message.from_user is None or message.bot is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Сначала /start.")
            return
        loc = get_locale(char, message.from_user.language_code)
        if not unlock_service.is_unlocked(char, "menu_sticker"):
            await message.answer(
                t(loc, "sticker_unlock_alert", level=unlock_service.UNLOCK_BY_KEY["menu_sticker"].level),
            )
            return
        ok, err = await _run_towercard_preview(
            session,
            bot=message.bot,
            chat_id=message.chat.id,
            char=char,
            state=state,
            loc=loc,
        )
        if not ok:
            await message.answer(err, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.exception("stickercard")
        await message.answer(
            f"Не удалось отправить карту: <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )


@router.message(Command("stickerhelp", "стикер_помощь"))
async def cmd_stickerhelp(message: Message, session: AsyncSession) -> None:
    """Кратко: карты башни, ATK/DEF, редкость, дуэльные стихии."""
    _ = session
    await message.answer(STICKER_MECHANICS_HTML, parse_mode=ParseMode.HTML)


# --- Админ: синхронизация имён стикерпака (getStickerSet) ---
@router.message(Command("admin_sticker_set"))
async def admin_sticker_set(message: Message, session: AsyncSession, command: CommandObject) -> None:
    """Список стикеров набора (для ручного кеша file_id). Только админ."""
    try:
        if message.from_user is None or not is_admin(message.from_user.id):
            return
        name = (command.args or "").strip()
        if not name:
            await message.answer(
                "Использование: <code>/admin_sticker_set имя_набора</code>\n"
                "По умолчанию в настройках набор: <code>BashnyaIspytanij</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        if message.bot is None:
            return
        st = await message.bot.get_sticker_set(name)
        lines = [f"Набор <b>{html.escape(name)}</b>, стикеров: {len(st.stickers)}", ""]
        for i, s in enumerate(st.stickers[:30]):
            em = html.escape(s.emoji or "")
            lines.append(f"{i + 1}. emoji={em}\n   <code>{html.escape(s.file_id)}</code>")
        if len(st.stickers) > 30:
            lines.append("…")
        await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"Ошибка API: {html.escape(str(e))}", parse_mode=ParseMode.HTML)
