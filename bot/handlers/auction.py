"""
Магазин (лоты игроков): /магазин, выставление из сумки, покупка по цене, личные предложения.
"""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNotFound
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.auction_kb import (
    auction_cancel_create_keyboard,
    auction_hub_keyboard,
    auction_vip_portrait_preview_keyboard,
    auction_vip_portraits_keyboard,
    auction_vip_portraits_screen_html,
    auction_lots_page_keyboard,
    auction_my_lots_keyboard,
    auction_reprice_cancel_keyboard,
    bag_slots_for_auction_keyboard,
    bag_slots_for_direct_offer_keyboard,
    direct_offer_keyboard,
    lot_seller_keyboard,
    viewer_lot_keyboard,
    _rarity_emoji_from_item_data,
)
from bot.states.auction_states import AuctionCreateStates
from bot.states.combat_states import CombatStates
from utils.telegram.game_ui import edit_game_message_content, push_game_ui
from db.repository import auction_repo, character_repo, inventory_repo, user_repo
from game.economy.market import LOT_DURATION_DAYS, _expires_at_utc
from game.items import item_categories
import services.economy.economy_service as economy_service
import services.progression.home_service as home_service
from utils.telegram.ui import format_inventory_item_html, format_number, item_bag_button_label

router = Router(name="auction")

AUCTION_PAGE_SIZE = 6


async def _clear_auction_fsm_only(state: FSMContext) -> None:
    """Не трогаем состояние боя и другие FSM."""
    st = await state.get_state()
    if st is not None and str(st).startswith("AuctionCreateStates"):
        await state.clear()


def _shop_intro_html() -> str:
    return (
        "🛒 <b>Магазин</b>\n\n"
        "🛒 <b>Обычный магазин</b> — расходники и зелья за 💰 золото.\n"
        "⭐ <b>VIP-магазин</b> — эксклюзивные облики за Telegram Stars.\n\n"
        "──────────────────\n"
        "<b>Торговля между игроками:</b>\n"
        f"Из сумки · до <b>{LOT_DURATION_DAYS}</b> дн. · налог <b>10%</b> · до <b>5</b> активных лотов.\n"
        "Лоты — фиксированная цена, покупка мгновенно.\n"
        "🎯 <b>Игроку по ID</b> — личное предложение адресату."
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
    start_p = int(lot.start_price)
    if getattr(lot, "target_char_id", None) is not None:
        return (
            f"<b>Личное предложение #{lot.id}</b> · продавец {html.escape(seller_name)}\n"
            f"~<b>{hrs}</b> ч · фикс. цена <b>{format_number(start_p)}</b> зол. "
            f"<i>(только адресат может купить или отказаться)</i>\n\n"
            f"{item_block}"
        )
    return (
        f"<b>Лот #{lot.id}</b> · {html.escape(seller_name)}\n"
        f"~<b>{hrs}</b> ч · цена <b>{format_number(start_p)}</b> зол. · <i>покупка сразу</i>\n\n"
        f"{item_block}"
    )


def _my_lots_html(lots: list, *, target_game_by_lot_id: dict[int, int | None] | None = None) -> str:
    lines = ["<b>Твои лоты</b>\n"]
    if not lots:
        lines.append("<i>История пуста.</i>")
        return "\n".join(lines)
    tmap = target_game_by_lot_id or {}
    for lot in lots:
        st = lot.status
        name = html.escape(str((lot.item_data or {}).get("name", "?"))[:40])
        lines.append(
            f"#{lot.id} · {name} · <i>{html.escape(st)}</i> · цена {format_number(int(lot.start_price))}",
        )
        if getattr(lot, "target_char_id", None) is not None:
            gid = tmap.get(int(lot.id))
            if gid is not None:
                lines.append(f"   🎯 личное предложение → игрок <b>ID {gid}</b>")
            else:
                lines.append("   🎯 личное предложение")
        if st == "active":
            cur = int(lot.current_bid)
            if cur > 0:
                lines.append(f"   продано / зарезервировано: {format_number(cur)}")
    lines.append(
        "\n<i>Снять лот или сменить цену можно, пока <b>никто не купил</b> "
        "(для личных предложений — пока адресат не купил и не отказался).</i>",
    )
    return "\n".join(lines)


async def _notify_direct_offer_target(
    bot,
    session: AsyncSession,
    lot,
    seller,
    target,
) -> None:
    """Сообщение адресату в Telegram после фиксации лота в БД."""
    buyer_user = await user_repo.get_by_id(session, int(target.user_id))
    if buyer_user is None or buyer_user.is_banned:
        return
    gid = int(seller.game_id) if seller.game_id is not None else 0
    price = int(lot.start_price)
    item_block = format_inventory_item_html(lot.item_data or {})
    text = (
        "🎯 <b>Личное предложение из магазина</b>\n"
        f"От <b>{html.escape(seller.display_name)}</b> (игровой ID <code>{gid}</code>)\n"
        f"Лот <b>#{lot.id}</b> · цена <b>{format_number(price)}</b> зол.\n\n"
        f"{item_block}\n\n"
        "<i>Налог 10% удерживается с продавца при продаже.</i>"
    )
    try:
        await bot.send_message(
            int(buyer_user.telegram_id),
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=direct_offer_keyboard(int(lot.id)),
        )
    except (TelegramForbiddenError, TelegramNotFound):
        pass
    except Exception:
        logger.exception("direct offer notify")


async def _notify_seller_auction_line(bot, session: AsyncSession, seller_char_id: int, html_line: str) -> None:
    seller = await character_repo.get_by_id(session, int(seller_char_id))
    if seller is None:
        return
    u = await user_repo.get_by_id(session, int(seller.user_id))
    if u is None or u.is_banned:
        return
    try:
        await bot.send_message(int(u.telegram_id), html_line, parse_mode=ParseMode.HTML)
    except (TelegramForbiddenError, TelegramNotFound):
        pass
    except Exception:
        logger.exception("seller auction notify")


def _parse_browse_cd(data: str | None) -> tuple[int, str]:
    parts = (data or "").split(":")
    if len(parts) >= 4 and parts[2].isdigit():
        return int(parts[2]), parts[3] if parts[3] in (
            item_categories.BAG_CAT_ALL,
            item_categories.BAG_CAT_EQUIP,
            item_categories.BAG_CAT_USE,
            item_categories.BAG_CAT_OTHER,
        ) else item_categories.BAG_CAT_ALL
    if len(parts) == 3 and parts[2].isdigit():
        return int(parts[2]), item_categories.BAG_CAT_ALL
    return 0, item_categories.BAG_CAT_ALL


def _parse_lot_detail_cd(data: str | None) -> tuple[int, int, str]:
    parts = (data or "").split(":")
    if len(parts) < 3 or not parts[2].isdigit():
        return 0, 0, item_categories.BAG_CAT_ALL
    lid = int(parts[2])
    page = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 0
    cat = (
        parts[4]
        if len(parts) >= 5
        and parts[4]
        in (
            item_categories.BAG_CAT_ALL,
            item_categories.BAG_CAT_EQUIP,
            item_categories.BAG_CAT_USE,
            item_categories.BAG_CAT_OTHER,
        )
        else item_categories.BAG_CAT_ALL
    )
    return lid, page, cat


def _parse_buy_cd(data: str | None) -> tuple[int, int, str]:
    parts = (data or "").split(":")
    if len(parts) < 5 or parts[1] != "buy" or not parts[2].isdigit():
        return 0, 0, item_categories.BAG_CAT_ALL
    lid = int(parts[2])
    page = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 0
    cat = (
        parts[4]
        if len(parts) >= 5
        and parts[4]
        in (
            item_categories.BAG_CAT_ALL,
            item_categories.BAG_CAT_EQUIP,
            item_categories.BAG_CAT_USE,
            item_categories.BAG_CAT_OTHER,
        )
        else item_categories.BAG_CAT_ALL
    )
    return lid, page, cat


@router.message(Command("auction"))
@router.message(Command("аукцион"))
@router.message(Command("магазин"))
@router.message(Command("shop"))
async def cmd_auction(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if message.from_user is None:
            return
        _, char = await _load_char(session, message.from_user.id)
        if char is None:
            await message.answer("Сначала создай героя через /start.")
            return
        fl = int(char.floor_number) if char else 1
        await message.answer(
            _shop_intro_html(),
            parse_mode=ParseMode.HTML,
            reply_markup=auction_hub_keyboard(fl),
        )
    except Exception:
        logger.exception("cmd_auction")
        await message.answer("Ошибка магазина.")


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
        fl = int(char.floor_number) if char else 1
        try:
            await edit_game_message_content(callback.message,
                _shop_intro_html(),
                parse_mode=ParseMode.HTML,
                reply_markup=auction_hub_keyboard(fl),
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        await callback.answer()
    except Exception:
        logger.exception("auc:hub")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "auc:prt")
async def auc_portraits(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """VIP-магазин: облики за Telegram Stars."""
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
            await edit_game_message_content(callback.message,
                auction_vip_portraits_screen_html(char),
                parse_mode=ParseMode.HTML,
                reply_markup=auction_vip_portraits_keyboard(int(char.floor_number)),
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        await callback.answer()
    except Exception:
        logger.exception("auc:prt")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("auc:vpr:"))
async def auc_vip_portrait_preview(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Предпросмотр VIP-облика перед покупкой за Stars."""
    try:
        await _clear_auction_fsm_only(state)
        if callback.message is None or callback.from_user is None or callback.data is None:
            await callback.answer()
            return
        parts = callback.data.split(":")
        if len(parts) < 4:
            await callback.answer()
            return
        fl = int(parts[2])
        gk = str(parts[3]).strip().lower()
        buy_origin = str(parts[4]).strip().lower()[:2] if len(parts) >= 5 else "a"
        if buy_origin not in ("a", "c", "f", "m", "h", "u"):
            buy_origin = "a"
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        from game.economy.shop import vip_good_by_key
        import services.economy.shop_service as shop_service
        from utils.media.image_assets import tower_bot_root
        from utils.media.profile_portraits import portrait_blurb_ru, portrait_path_if_exists, portrait_title_ru

        g = vip_good_by_key(gk)
        if g is None:
            await callback.answer("Товар не найден.", show_alert=True)
            return
        vs = str(g.item_data.get("virtual_shop") or "")
        pk = str(g.item_data.get("portrait_key") or "").strip()
        rel_preview = str(g.item_data.get("preview_image") or "").strip()

        img: str | None = None
        if vs == "vip_star_bonus":
            bid = str(g.item_data.get("vip_bonus_id") or "").strip()
            already_owned = shop_service.vip_bonus_owned(char, bid) if bid else False
            if rel_preview:
                p = tower_bot_root() / rel_preview
                if p.is_file():
                    img = str(p)
            name = html.escape(g.name)
            raw_blurb = g.blurb
        else:
            already_owned = bool(pk and home_service.has_portrait_unlock(char, pk))
            _p = portrait_path_if_exists(pk) if pk else None
            img = str(_p) if _p else None
            name = html.escape(portrait_title_ru(pk) if pk else g.name)
            raw_blurb = portrait_blurb_ru(pk) if pk else g.blurb

        plain_blurb = re.sub(r"<[^>]*>", "", str(raw_blurb or "")).strip()
        blurb_body = html.escape(plain_blurb).replace("\n", "<br/>")
        caption = (
            f"{g.emoji} <b>{name}</b>\n\n"
            f"{blurb_body}\n\n"
            f"Цена: <b>{g.stars_price} ⭐ Telegram Stars</b>"
        )
        if already_owned:
            if vs == "vip_star_bonus":
                caption += "\n\n✅ Уже активирован."
            else:
                caption += "\n\n✅ Уже в твоём гардеробе."
        elif img is None:
            caption += "\n\n⚠️ Изображение пока не загружено."
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=caption,
            reply_markup=auction_vip_portrait_preview_keyboard(
                fl, g.key,
                stars_price=g.stars_price,
                already_owned=already_owned,
                buy_origin=buy_origin,
            ),
            target_message=callback.message,
            photo_path=img,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:vpr")
        await callback.answer("Ошибка.", show_alert=True)


# Оставляем auc:prv: для обратной совместимости — перенаправляем на vpr
@router.callback_query(F.data.startswith("auc:prv:"))
async def auc_portrait_preview_legacy(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Редирект со старого колбэка на новый VIP-превью."""
    if callback.data:
        # auc:prv:{fl}:{key} → auc:vpr:{fl}:{key}
        new_data = callback.data.replace("auc:prv:", "auc:vpr:", 1)
        callback.data = new_data
    await auc_vip_portrait_preview(callback, session, state)


@router.callback_query(F.data == "auc:prvown")
async def auc_portrait_already_owned_stub(callback: CallbackQuery) -> None:
    """Кнопка при уже купленном VIP-товаре из превью."""
    await callback.answer("Этот товар уже куплен.", show_alert=True)


@router.callback_query(F.data.startswith("auc:create"))
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
        parts = (callback.data or "").split(":")
        bag_cat = (
            parts[2]
            if len(parts) >= 3
            and parts[2]
            in (
                item_categories.BAG_CAT_ALL,
                item_categories.BAG_CAT_EQUIP,
                item_categories.BAG_CAT_USE,
                item_categories.BAG_CAT_OTHER,
            )
            else item_categories.BAG_CAT_ALL
        )
        bag = await inventory_repo.list_bag_items(session, char.id)
        filtered = [it for it in bag if item_categories.item_data_matches_bag_category(it.item_data, bag_cat)]
        if not filtered:
            await callback.answer("В этой категории нет предметов в сумке.", show_alert=True)
            return
        pairs: list[tuple[int, str]] = []
        for it in sorted(filtered, key=lambda x: (x.bag_slot or 0)):
            slot = int(it.bag_slot or 0)
            pairs.append((slot, item_bag_button_label(it.item_data, slot)))
        text = _shop_intro_html() + "\n<b>Ячейка сумки</b> (предмет уйдёт в лот):"
        await edit_game_message_content(callback.message,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=bag_slots_for_auction_keyboard(pairs, bag_cat=bag_cat),
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
        text = f"{preview}\n\n<b>Цена лота</b> — одним сообщением, золото (целое ≥ 1)."
        await edit_game_message_content(callback.message,
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
            await message.answer("Нужно целое число — цена лота в золоте.")
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


@router.message(StateFilter(AuctionCreateStates.waiting_reprice), F.text)
async def auc_reprice_input(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        _, char = await _load_char(session, message.from_user.id)
        if char is None:
            await state.clear()
            await message.answer("Нет персонажа.")
            return
        raw = (message.text or "").strip().replace(" ", "").replace("\u00a0", "")
        if not raw.isdigit():
            await message.answer("Нужно целое число — новая цена в золоте.")
            return
        price = int(raw)
        data = await state.get_data()
        lot_id = int(data.get("auc_reprice_lot_id", 0))
        await state.clear()
        if lot_id <= 0:
            await message.answer("Сессия устарела. Открой магазин снова.")
            return
        ok, payload = await economy_service.auction_seller_reprice_lot(session, char, lot_id, price)
        await message.answer(payload, reply_markup=auction_hub_keyboard())
    except Exception:
        logger.exception("auc_reprice_input")
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
        page, cat = _parse_browse_cd(callback.data)
        total = await auction_repo.count_active_visible(session, category=cat)
        lots = await auction_repo.list_active(
            session,
            limit=AUCTION_PAGE_SIZE,
            offset=page * AUCTION_PAGE_SIZE,
            category=cat,
        )
        text = _shop_intro_html() + f"\n<b>Каталог</b> ({total})\n"
        if not lots:
            text += "<i>Сейчас нет лотов в этой категории.</i>"
        await edit_game_message_content(callback.message,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=auction_lots_page_keyboard(
                lots,
                page=page,
                total=total,
                page_size=AUCTION_PAGE_SIZE,
                category=cat,
            ),
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
        lid, browse_page, browse_cat = _parse_lot_detail_cd(callback.data)
        if lid <= 0:
            await callback.answer()
            return
        lot = await auction_repo.get_by_id(session, lid)
        if lot is None or lot.status != "active":
            await callback.answer("Лот недоступен.", show_alert=True)
            return
        exp = _expires_at_utc(lot.expires_at)
        if datetime.now(UTC) >= exp:
            await callback.answer("Лот истёк.", show_alert=True)
            return
        if getattr(lot, "target_char_id", None) is not None:
            tid = int(lot.target_char_id)
            sid = int(lot.seller_char_id)
            if int(char.id) not in (tid, sid):
                await callback.answer("Это частный лот — доступ только продавцу и адресату.", show_alert=True)
                return
        seller = await character_repo.get_by_id(session, int(lot.seller_char_id))
        seller_name = seller.display_name if seller else "???"
        body = _lot_detail_html(lot, seller_name)
        kb = viewer_lot_keyboard(
            lot,
            int(char.id),
            browse_page=browse_page,
            browse_cat=browse_cat,
        )
        await edit_game_message_content(callback.message,
            body,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:lot")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("auc:cnl:"))
async def auc_cancel_lot(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        ok, msg = await economy_service.auction_seller_cancel_lot(session, char, int(lid_s))
        await callback.answer(msg[:200], show_alert=not ok)
        if ok:
            try:
                await edit_game_message_content(callback.message,
                    _shop_intro_html() + f"\n\n{html.escape(msg)}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=auction_hub_keyboard(),
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    _shop_intro_html() + f"\n\n{html.escape(msg)}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=auction_hub_keyboard(),
                )
    except Exception:
        logger.exception("auc:cnl")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("auc:repr:"))
async def auc_reprice_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        lid_s = (callback.data or "").split(":")[-1]
        if not lid_s.isdigit():
            await callback.answer()
            return
        lid = int(lid_s)
        lot = await auction_repo.get_by_id(session, lid)
        if lot is None or int(lot.seller_char_id) != int(char.id) or lot.status != "active":
            await callback.answer("Лот недоступен.", show_alert=True)
            return
        if int(lot.current_bid) > 0 or lot.buyer_char_id is not None:
            await callback.answer("Лот уже куплен — цену менять нельзя.", show_alert=True)
            return
        await state.set_state(AuctionCreateStates.waiting_reprice)
        await state.update_data(auc_reprice_lot_id=lid)
        preview = format_inventory_item_html(lot.item_data or {})
        cur = int(lot.start_price)
        text = (
            f"{preview}\n\n"
            f"<b>Лот #{lid}</b> · текущая цена: <b>{format_number(cur)}</b> зол.\n"
            f"Напиши в чат <b>одним числом</b> новую цену (≥ 1)."
        )
        await edit_game_message_content(callback.message,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=auction_reprice_cancel_keyboard(lid),
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:repr")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("auc:buy:"))
async def auc_buy(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if callback.from_user is None:
            await callback.answer()
            return
        if callback.message is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        lid, _browse_page, _browse_cat = _parse_buy_cd(callback.data)
        if lid <= 0:
            await callback.answer()
            return
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        ok, msg = await economy_service.auction_buy_lot_now(session, char, lid)
        if ok:
            await session.commit()
        await session.refresh(char)
        await callback.answer(msg[:200], show_alert=not ok)
        if ok:
            try:
                await edit_game_message_content(callback.message,
                    _shop_intro_html() + f"\n\n✅ {html.escape(msg)}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=auction_hub_keyboard(),
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    f"✅ {msg}",
                    reply_markup=auction_hub_keyboard(),
                )
    except Exception:
        logger.exception("auc:buy")
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
        tmap: dict[int, int | None] = {}
        for lot in lots:
            if getattr(lot, "target_char_id", None):
                tc = await character_repo.get_by_id(session, int(lot.target_char_id))
                tmap[int(lot.id)] = int(tc.game_id) if tc and tc.game_id is not None else None
        text = _my_lots_html(lots, target_game_by_lot_id=tmap)
        active_lots = [
            (
                int(l.id),
                int(l.start_price),
                _rarity_emoji_from_item_data(l.item_data if isinstance(l.item_data, dict) else None),
            )
            for l in lots
            if l.status == "active"
        ]
        await edit_game_message_content(callback.message,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=auction_my_lots_keyboard(active_lots),
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:my")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "auc:direct")
async def auc_direct_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        await state.set_state(AuctionCreateStates.waiting_direct_game_id)
        await state.update_data(auc_direct_flow=1)
        text = (
            _shop_intro_html()
            + "\n\n🎯 <b>Личное предложение</b>\n"
            "Напиши в чат <b>одним числом</b> <b>игровой ID</b> получателя "
            "(его можно посмотреть в профиле / статусе героя — публичный номер игрока)."
        )
        await edit_game_message_content(callback.message,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=auction_cancel_create_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:direct")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("auc:directbag:"))
async def auc_direct_bag(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() != AuctionCreateStates.waiting_direct_slot.state:
            await callback.answer("Сначала начни с кнопки «Игроку по ID».", show_alert=True)
            return
        data = await state.get_data()
        if not data.get("auc_direct_target_char_id"):
            await callback.answer("Сессия устарела.", show_alert=True)
            return
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        parts = (callback.data or "").split(":")
        bag_cat = (
            parts[2]
            if len(parts) >= 3
            and parts[2]
            in (
                item_categories.BAG_CAT_ALL,
                item_categories.BAG_CAT_EQUIP,
                item_categories.BAG_CAT_USE,
                item_categories.BAG_CAT_OTHER,
            )
            else item_categories.BAG_CAT_ALL
        )
        bag = await inventory_repo.list_bag_items(session, char.id)
        filtered = [it for it in bag if item_categories.item_data_matches_bag_category(it.item_data, bag_cat)]
        if not filtered:
            await callback.answer("В этой категории нет предметов в сумке.", show_alert=True)
            return
        pairs: list[tuple[int, str]] = []
        for it in sorted(filtered, key=lambda x: (x.bag_slot or 0)):
            slot = int(it.bag_slot or 0)
            pairs.append((slot, item_bag_button_label(it.item_data, slot)))
        text = _shop_intro_html() + "\n\n<b>Ячейка сумки</b> для личного предложения:"
        await edit_game_message_content(callback.message,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=bag_slots_for_direct_offer_keyboard(pairs, bag_cat=bag_cat),
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:directbag")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("auc:dpick:"))
async def auc_direct_pick_slot(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.from_user is None:
            await callback.answer()
            return
        if await state.get_state() != AuctionCreateStates.waiting_direct_slot.state:
            await callback.answer("Сначала введи ID и выбери категорию.", show_alert=True)
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
        await state.set_state(AuctionCreateStates.waiting_direct_price)
        await state.update_data(auc_direct_bag_slot=slot)
        preview = format_inventory_item_html(it.item_data or {})
        text = f"{preview}\n\n<b>Цена для адресата</b> — одним сообщением, золото (целое ≥ 1)."
        await edit_game_message_content(callback.message,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=auction_cancel_create_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("auc:dpick")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(StateFilter(AuctionCreateStates.waiting_direct_game_id), F.text)
async def auc_direct_game_id_input(message: Message, session: AsyncSession, state: FSMContext) -> None:
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
            await message.answer("Нужно целое число — игровой ID из профиля героя.")
            return
        gid = int(raw)
        target = await character_repo.get_by_game_id(session, gid)
        if target is None:
            await message.answer("Игрок с таким ID не найден (или аккаунт недоступен).")
            return
        if int(target.id) == int(char.id):
            await message.answer("Нельзя отправить предложение самому себе.")
            return
        await state.set_state(AuctionCreateStates.waiting_direct_slot)
        await state.update_data(auc_direct_target_char_id=int(target.id), auc_direct_target_game_id=gid)
        bag = await inventory_repo.list_bag_items(session, char.id)
        if not bag:
            await state.clear()
            await message.answer("В сумке нет предметов.")
            return
        filtered = [it for it in bag if item_categories.item_data_matches_bag_category(it.item_data, item_categories.BAG_CAT_ALL)]
        pairs: list[tuple[int, str]] = []
        for it in sorted(filtered, key=lambda x: (x.bag_slot or 0)):
            slot = int(it.bag_slot or 0)
            pairs.append((slot, item_bag_button_label(it.item_data, slot)))
        text = (
            _shop_intro_html()
            + f"\n\nАдресат: игровой ID <b>{gid}</b> · {html.escape(target.display_name)}\n"
            "<b>Ячейка сумки</b> (предмет уйдёт в предложение):"
        )
        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=bag_slots_for_direct_offer_keyboard(pairs, bag_cat=item_categories.BAG_CAT_ALL),
        )
    except Exception:
        logger.exception("auc_direct_game_id_input")
        await state.clear()
        await message.answer("Ошибка.")


@router.message(StateFilter(AuctionCreateStates.waiting_direct_price), F.text)
async def auc_direct_price_input(message: Message, session: AsyncSession, state: FSMContext) -> None:
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
            await message.answer("Нужно целое число — цена в золоте.")
            return
        price = int(raw)
        data = await state.get_data()
        slot = int(data.get("auc_direct_bag_slot", -1))
        tid = int(data.get("auc_direct_target_char_id", 0))
        await state.clear()
        if slot < 0 or tid <= 0:
            await message.answer("Сессия устарела. Открой магазин снова.")
            return
        target = await character_repo.get_by_id(session, tid)
        if target is None:
            await message.answer("Получатель не найден.")
            return
        ok, msg, lot_obj = await economy_service.auction_create_direct_offer_lot(
            session, char, slot, price, target
        )
        if not ok or lot_obj is None:
            await message.answer(msg, reply_markup=auction_hub_keyboard())
            return
        await session.commit()
        if message.bot is not None:
            await _notify_direct_offer_target(message.bot, session, lot_obj, char, target)
        await message.answer(msg, reply_markup=auction_hub_keyboard())
    except Exception:
        logger.exception("auc_direct_price_input")
        await state.clear()
        await message.answer("Ошибка.")


@router.callback_query(F.data.startswith("auc:dacc:"))
async def auc_direct_accept(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        lid_s = (callback.data or "").split(":")[-1]
        if not lid_s.isdigit():
            await callback.answer()
            return
        lid = int(lid_s)
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        ok, msg = await economy_service.auction_accept_direct_offer(session, char, lid)
        if ok:
            await session.commit()
        await callback.answer(msg[:200], show_alert=not ok)
        if ok and callback.bot is not None:
            lot = await auction_repo.get_by_id(session, lid)
            if lot is not None:
                await _notify_seller_auction_line(
                    callback.bot,
                    session,
                    int(lot.seller_char_id),
                    f"✅ Игрок <b>{html.escape(char.display_name)}</b> купил личное предложение "
                    f"<b>#{lid}</b> за <b>{format_number(int(lot.start_price))}</b> зол.",
                )
        if ok:
            try:
                await edit_game_message_content(callback.message,
                    f"✅ {html.escape(msg)}\n\nОткрой 🛒 <b>Магазин</b> в меню при необходимости.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=auction_hub_keyboard(),
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    f"✅ {msg}",
                    reply_markup=auction_hub_keyboard(),
                )
    except Exception:
        logger.exception("auc:dacc")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("auc:ddec:"))
async def auc_direct_decline(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clear_auction_fsm_only(state)
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        lid_s = (callback.data or "").split(":")[-1]
        if not lid_s.isdigit():
            await callback.answer()
            return
        lid = int(lid_s)
        _, char = await _load_char(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        ok, msg = await economy_service.auction_decline_direct_offer(session, char, lid)
        if ok:
            await session.commit()
        await callback.answer(msg[:200], show_alert=not ok)
        if ok and callback.bot is not None:
            lot = await auction_repo.get_by_id(session, lid)
            if lot is not None:
                seller_id = int(lot.seller_char_id)
                await _notify_seller_auction_line(
                    callback.bot,
                    session,
                    seller_id,
                    f"❌ Игрок <b>{html.escape(char.display_name)}</b> отказался от личного предложения "
                    f"<b>#{lid}</b>. Предмет возвращён в твою сумку.",
                )
        if ok:
            try:
                await edit_game_message_content(callback.message,
                    f"❌ {html.escape(msg)}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=auction_hub_keyboard(),
                )
            except TelegramBadRequest:
                await callback.message.answer(f"❌ {msg}", reply_markup=auction_hub_keyboard())
    except Exception:
        logger.exception("auc:ddec")
        await callback.answer("Ошибка.", show_alert=True)
