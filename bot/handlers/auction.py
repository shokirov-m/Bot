"""
Аукцион: /auction, выставление из сумки, ставки, мои лоты.
"""

from __future__ import annotations

import html
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.auction_kb import (
    auction_cancel_create_keyboard,
    auction_hub_keyboard,
    auction_lots_page_keyboard,
    auction_my_lots_keyboard,
    bag_slots_for_auction_keyboard,
    lot_bid_keyboard,
)
from bot.states.auction_states import AuctionCreateStates
from bot.states.combat_states import CombatStates
from db.repository import auction_repo, character_repo, inventory_repo, user_repo
from game.economy.market import LOT_DURATION_DAYS, min_next_bid_for_lot
from services import economy_service
from utils.ui import format_inventory_item_html, format_number, item_bag_button_label

router = Router(name="auction")

AUCTION_PAGE_SIZE = 6


async def _clear_auction_fsm_only(state: FSMContext) -> None:
    """Не трогаем состояние боя и другие FSM."""
    st = await state.get_state()
    if st is not None and st.startswith("AuctionCreateStates"):
        await state.clear()


def _auction_intro_html() -> str:
    return (
        "🏛️ <b>Аукцион</b>\n"
        f"Из сумки · до <b>{LOT_DURATION_DAYS}</b> дн. · комиссия <b>5%</b> · активных лотов — до <b>5</b>."
    )


async def _load_char(session: AsyncSession, telegram_id: int):
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None, None
    char = await character_repo.get_by_user_id(session, user.id)
    return user, char


def _lot_detail_html(lot, seller_name: str) -> str:
    left = lot.expires_at
    if left.tzinfo is None:
        left = left.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    hrs = max(0, int((left - now).total_seconds() // 3600))
    item_block = format_inventory_item_html(lot.item_data or {})
    cur = int(lot.current_bid)
    nxt = min_next_bid_for_lot(lot)
    leader = "ставок пока нет" if cur <= 0 else f"{format_number(cur)} зол."
    return (
        f"<b>Лот #{lot.id}</b> · {html.escape(seller_name)}\n"
        f"~<b>{hrs}</b> ч · ставка: <b>{leader}</b> · от <b>{format_number(nxt)}</b> зол.\n\n"
        f"{item_block}"
    )


def _my_lots_html(lots: list) -> str:
    lines = ["<b>Твои лоты</b>\n"]
    if not lots:
        lines.append("<i>История пуста.</i>")
        return "\n".join(lines)
    for lot in lots:
        st = lot.status
        name = html.escape(str((lot.item_data or {}).get("name", "?"))[:40])
        lines.append(
            f"#{lot.id} · {name} · <i>{html.escape(st)}</i> · старт {format_number(int(lot.start_price))}",
        )
        if st == "active":
            cur = int(lot.current_bid)
            if cur > 0:
                lines.append(f"   текущая ставка: {format_number(cur)}")
    return "\n".join(lines)


@router.message(Command("auction"))
@router.message(Command("аукцион"))
async def cmd_auction(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if message.from_user is None:
            return
        _, char = await _load_char(session, message.from_user.id)
        if char is None:
            await message.answer("Сначала создай героя через /start.")
            return
        await message.answer(
            _auction_intro_html(),
            parse_mode=ParseMode.HTML,
            reply_markup=auction_hub_keyboard(),
        )
    except Exception:
        logger.exception("cmd_auction")
        await message.answer("Ошибка аукциона.")


@router.callback_query(F.data == "auc:hub")
async def auc_hub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        try:
            await callback.message.edit_text(
                _auction_intro_html(),
                parse_mode=ParseMode.HTML,
                reply_markup=auction_hub_keyboard(),
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        await callback.answer()
    except Exception:
        logger.exception("auc:hub")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "auc:create")
async def auc_create_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        bag = await inventory_repo.list_bag_items(session, char.id)
        if not bag:
            await callback.answer("В сумке нет предметов.", show_alert=True)
            return
        pairs: list[tuple[int, str]] = []
        for it in sorted(bag, key=lambda x: (x.bag_slot or 0)):
            slot = int(it.bag_slot or 0)
            pairs.append((slot, item_bag_button_label(it.item_data, slot)))
        text = _auction_intro_html() + "\n<b>Ячейка сумки</b> (предмет уйдёт в лот):"
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=bag_slots_for_auction_keyboard(pairs),
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:create")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("auc:pick:"))
async def auc_pick_slot(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        slot_s = (callback.data or "").split(":")[-1]
        if not slot_s.isdigit():
            await callback.answer()
            return
        slot = int(slot_s)
        it = await inventory_repo.get_bag_item_at_slot(session, char.id, slot)
        if it is None:
            await callback.answer("Ячейка пуста.", show_alert=True)
            return
        await state.set_state(AuctionCreateStates.waiting_price)
        await state.update_data(auc_bag_slot=slot)
        preview = format_inventory_item_html(it.item_data or {})
        text = f"{preview}\n\n<b>Стартовая цена</b> — одним сообщением, золото (целое ≥ 1)."
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=auction_cancel_create_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:pick")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(StateFilter(AuctionCreateStates.waiting_price), F.text)
async def auc_price_input(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await state.clear()
            await message.answer("Сначала заверши бой.")
            return
        _, char = await _load_char(session, message.from_user.id)
        if char is None:
            await state.clear()
            await message.answer("Нет персонажа.")
            return
        raw = (message.text or "").strip().replace(" ", "").replace("\u00a0", "")
        if not raw.isdigit():
            await message.answer("Нужно целое число — стартовая цена в золоте.")
            return
        price = int(raw)
        data = await state.get_data()
        slot = int(data.get("auc_bag_slot", -1))
        await state.clear()
        _ok, payload = await economy_service.auction_create_lot(session, char, slot, price)
        await message.answer(payload, reply_markup=auction_hub_keyboard())
    except Exception:
        logger.exception("auc_price_input")
        await state.clear()
        await message.answer("Ошибка.")


@router.callback_query(F.data.startswith("auc:browse:"))
async def auc_browse(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        page_s = (callback.data or "").split(":")[-1]
        page = int(page_s) if page_s.isdigit() else 0
        total = await auction_repo.count_active_visible(session)
        lots = await auction_repo.list_active(
            session,
            limit=AUCTION_PAGE_SIZE,
            offset=page * AUCTION_PAGE_SIZE,
        )
        text = _auction_intro_html() + f"\n<b>Лоты</b> ({total})\n"
        if not lots:
            text += "<i>Сейчас нет лотов.</i>"
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=auction_lots_page_keyboard(lots, page=page, total=total, page_size=AUCTION_PAGE_SIZE),
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:browse")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("auc:lot:"))
async def auc_lot_detail(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        lid_s = (callback.data or "").split(":")[-1]
        if not lid_s.isdigit():
            await callback.answer()
            return
        lot = await auction_repo.get_by_id(session, int(lid_s))
        if lot is None or lot.status != "active":
            await callback.answer("Лот недоступен.", show_alert=True)
            return
        exp = lot.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        if datetime.now(UTC) >= exp:
            await callback.answer("Лот истёк.", show_alert=True)
            return
        seller = await character_repo.get_by_id(session, int(lot.seller_char_id))
        seller_name = seller.display_name if seller else "???"
        body = _lot_detail_html(lot, seller_name)
        await callback.message.edit_text(
            body,
            parse_mode=ParseMode.HTML,
            reply_markup=lot_bid_keyboard(lot),
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:lot")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("auc:bid:"))
async def auc_bid(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        parts = (callback.data or "").split(":")
        if len(parts) != 4 or parts[1] != "bid":
            await callback.answer()
            return
        lot_id_s, amt_s = parts[2], parts[3]
        if not lot_id_s.isdigit() or not amt_s.isdigit():
            await callback.answer()
            return
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        ok, msg = await economy_service.auction_place_bid(session, char, int(lot_id_s), int(amt_s))
        await session.refresh(char)
        await callback.answer(msg[:200], show_alert=not ok)
        if callback.message is not None and ok:
            lot = await auction_repo.get_by_id(session, int(lot_id_s))
            exp = lot.expires_at if lot else None
            if exp is not None and exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            if (
                lot
                and lot.status == "active"
                and exp is not None
                and datetime.now(UTC) < exp
            ):
                seller = await character_repo.get_by_id(session, int(lot.seller_char_id))
                seller_name = seller.display_name if seller else "???"
                try:
                    await callback.message.edit_text(
                        _lot_detail_html(lot, seller_name),
                        parse_mode=ParseMode.HTML,
                        reply_markup=lot_bid_keyboard(lot),
                    )
                except TelegramBadRequest:
                    pass
    except Exception:
        logger.exception("auc:bid")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "auc:my")
async def auc_my(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        lots = await auction_repo.list_seller_lots(session, char.id, limit=25)
        text = _my_lots_html(lots)
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=auction_my_lots_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:my")
        await callback.answer("Ошибка.", show_alert=True)
