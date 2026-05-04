"""PvE Колизей: последовательные бои (col:*)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.coliseum_kb import (
    _batch_range,
    coliseum_fight_confirm_keyboard,
    coliseum_main_keyboard,
)
from bot.utils.game_art import coliseum_fighter_photo_path, coliseum_hub_photo_path
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, user_repo
from game.coliseum.coliseum_data import fighter_by_id, scaled_coliseum_atk
from services import coliseum_service, combat_service

router = Router(name="coliseum")


def _menu_html(char) -> str:
    defeated = coliseum_service.defeated_ids(char)
    nxt = coliseum_service.next_fighter_id(char)
    prog = len(defeated)
    a, b = _batch_range(next_id=nxt)
    return (
        "🏛️ <b>Колизей</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Прогресс: <b>{prog}</b> / 50\n"
        f"{'Следующий по очереди: <b>#' + str(nxt) + '</b>' if nxt else '<b>Все повержены!</b>'}\n\n"
        "Бои идут по порядку: требуется уровень героя и победа над предыдущим бойцом.\n"
        "Чемпионы (каждый 10-й) дают ×2 золота и опыта.\n"
        f"<i>Сейчас в списке: боецы <b>#{a}–#{b}</b> (после побед над пятёркой — следующие 5).</i>"
    )


@router.callback_query(F.data == "mnu:col")
@router.callback_query(F.data == "col:menu")
async def coliseum_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.from_user is None or callback.message is None or callback.bot is None:
        await callback.answer()
        return
    user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
    if user is None or user.is_banned:
        await callback.answer("Нет доступа.", show_alert=True)
        return
    char = await character_repo.get_by_user_id(session, user.id)
    if char is None:
        await callback.answer("Сначала /start.", show_alert=True)
        return
    body = _menu_html(char)
    nxt = coliseum_service.next_fighter_id(char)
    ok, _ = coliseum_service.can_start_fight(char, nxt) if nxt else (False, "")
    kb = coliseum_main_keyboard(character=char, next_id=nxt, can_fight=ok)
    try:
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=kb,
            target_message=callback.message,
            photo_path=coliseum_hub_photo_path(),
            character=char,
        )
    except Exception:
        logger.exception("coliseum_menu")
    await callback.answer()


@router.callback_query(F.data == "col:rules")
async def coliseum_rules(callback: CallbackQuery) -> None:
    await callback.answer(
        "50 последовательных бойцов. Стамина — как в обычном бою. "
        "Поражение без штрафов золота и смерти.",
        show_alert=True,
    )


@router.callback_query(F.data == "col:noop")
async def coliseum_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.regexp(r"^col:info:\d+$"))
async def coliseum_info(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.message is None or callback.bot is None or callback.from_user is None:
        await callback.answer()
        return
    fid = int(str(callback.data).split(":")[-1])
    fdef = fighter_by_id(fid)
    if fdef is None:
        await callback.answer()
        return
    user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
    char = await character_repo.get_by_user_id(session, user.id) if user else None
    can, reason = coliseum_service.can_start_fight(char, fid) if char else (False, "")
    lines = [
        f"#{fdef.id} <b>{fdef.name}</b>",
        f"💬 <i>{fdef.phrase}</i>",
        f"❤️ HP {fdef.hp} · ⚔️ ATK {scaled_coliseum_atk(fdef)} · 🛡️ DEF {fdef.defense}",
        f"📈 Награда (база): {fdef.exp_reward} XP, {fdef.gold_reward} золота"
        + (" · 🏆 чемпион ×2" if fdef.is_champion else ""),
        f"Требуется ур. {fdef.required_level}",
    ]
    if not can and char is not None:
        lines.append(f"\n⚠️ {reason}")
    body = "\n".join(lines)
    from aiogram.types import InlineKeyboardMarkup
    from aiogram.types import InlineKeyboardButton as IB

    rows = [[IB(text="⬅️ К списку", callback_data="col:menu")]]
    if can:
        rows.insert(
            0,
            [IB(text="⚔️ Бой", callback_data=f"col:fight:{fid}")],
        )
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=kb,
            target_message=callback.message,
            photo_path=coliseum_fighter_photo_path(fid) or coliseum_hub_photo_path(),
            character=char,
        )
    except Exception:
        logger.exception("coliseum_info")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^col:fight:\d+$"))
async def coliseum_fight_ask(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.message is None or callback.bot is None or callback.from_user is None:
        await callback.answer()
        return
    fid = int(str(callback.data).split(":")[-1])
    fdef = fighter_by_id(fid)
    if fdef is None:
        await callback.answer()
        return
    user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
    char = await character_repo.get_by_user_id(session, user.id) if user else None
    body = (
        f"Начать бой с <b>{fdef.name}</b>?\n"
        f"Будет потрачена <b>1</b> стамина."
    )
    try:
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=coliseum_fight_confirm_keyboard(fid),
            target_message=callback.message,
            photo_path=coliseum_fighter_photo_path(fid) or coliseum_hub_photo_path(),
            character=char,
        )
    except Exception:
        logger.exception("coliseum_fight_ask")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^col:go:\d+$"))
async def coliseum_go(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    fid = int(str(callback.data).split(":")[-1])
    user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
    if user is None:
        await callback.answer()
        return
    char = await character_repo.get_by_user_id(session, user.id)
    if char is None:
        await callback.answer()
        return
    await combat_service.start_coliseum_combat(
        query=callback,
        session=session,
        state=state,
        character=char,
        fighter_id=fid,
    )
    # Ответ на callback полностью внутри start_coliseum_combat (успех и любая ошибка).
