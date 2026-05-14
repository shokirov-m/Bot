"""
Торговля: обычная лавка (золото) и VIP-магазин (Telegram Stars).
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.auction_kb import auction_portraits_keyboard, auction_portraits_screen_html
from bot.keyboards.shop_kb import shop_main_keyboard, shop_vip_keyboard
from bot.utils.game_art import menu_auction_photo_path, menu_shop_photo_path, menu_shop_vip_photo_path
from bot.utils.game_ui import push_game_ui
from config import settings
from db.repository import character_repo, user_repo
from game.economy import shop as shop_data
from services import shop_service
from utils.ui import LINE_SEP

router = Router(name="shop")


async def _load_char(session: AsyncSession, telegram_id: int):
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None
    return await character_repo.get_by_user_id(session, user.id)


def _origin_ok(s: str) -> str:
    return s if s in ("c", "f", "m", "h", "u", "a") else "f"


async def _shop_push_ui(
    state: FSMContext,
    query: CallbackQuery,
    char,
    text: str,
    reply_markup,
    *,
    vip: bool = False,
    auction_branch: bool = False,
) -> None:
    if query.message is None or query.bot is None:
        return
    if auction_branch:
        pp = menu_auction_photo_path()
    elif vip:
        pp = menu_shop_vip_photo_path()
    else:
        pp = menu_shop_photo_path()
    await push_game_ui(
        state,
        query.bot,
        chat_id=query.message.chat.id,
        text=text,
        reply_markup=reply_markup,
        target_message=query.message,
        photo_path=pp,
        character=char,
    )


# ---------------------------------------------------------------------------
# Обычный магазин
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("shp:main:"))
async def shop_open(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None or query.bot is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        origin = _origin_ok(parts[3]) if len(parts) > 3 else "f"
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Ты не здесь. Обнови /floor.", show_alert=True)
            return
        if origin not in ("h", "u", "a") and not shop_data.shop_available_on_floor(char.floor_number):
            await query.answer("Здесь нет торговца.", show_alert=True)
            return
        if origin == "a":
            await _shop_push_ui(
                state,
                query,
                char,
                auction_portraits_screen_html(char),
                auction_portraits_keyboard(int(char.floor_number)),
                auction_branch=True,
            )
            await query.answer()
            return
        text = shop_service.format_shop_welcome_html(char, from_city=(origin in ("c", "m")))
        if origin == "h":
            text = "🏠 <i>Заказ из дома</i> — те же цены по этажу героя.\n\n" + text
        elif origin == "u":
            text = "🏪 <i>Лавка главного меню</i> — цены как на твоём текущем этаже.\n\n" + text
        await _shop_push_ui(
            state,
            query,
            char,
            text,
            shop_main_keyboard(char.floor_number, origin),
        )
        await query.answer()
    except Exception:
        logger.exception("shp:main")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("shp:buy:"))
async def shop_buy(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None or query.bot is None:
            await query.answer()
            return
        parts = query.data.split(":")
        if len(parts) < 5:
            await query.answer()
            return
        floor_key = int(parts[2])
        good_key = parts[3]
        origin = _origin_ok(parts[4])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Этаж устарел.", show_alert=True)
            return

        allow_remote = origin in ("h", "u", "a")
        ok, payload = await shop_service.try_buy_good(
            session,
            char,
            good_key,
            expected_floor=floor_key,
            allow_remote_shop=allow_remote,
        )
        if not ok:
            await query.answer(payload[:180], show_alert=True)
            return

        if origin == "a":
            await session.refresh(char)
            await _shop_push_ui(
                state,
                query,
                char,
                auction_portraits_screen_html(char) + "\n\n" + LINE_SEP + "\n" + payload,
                auction_portraits_keyboard(int(char.floor_number)),
                auction_branch=True,
            )
            await query.answer("Куплено!")
            return

        header = shop_service.format_shop_welcome_html(char, from_city=(origin in ("c", "m")))
        if origin == "h":
            header = "🏠 <i>Заказ из дома</i>\n\n" + header
        elif origin == "u":
            header = "🏪 <i>Лавка главного меню</i>\n\n" + header
        await _shop_push_ui(
            state,
            query,
            char,
            f"{header}\n\n{LINE_SEP}\n{payload}",
            shop_main_keyboard(char.floor_number, origin),
        )
        await query.answer("Куплено!")
    except Exception:
        logger.exception("shp:buy")
        await query.answer("Ошибка.", show_alert=True)

# ---------------------------------------------------------------------------
# VIP-магазин (Telegram Stars)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("shp:vip:"))
async def shop_vip_open(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Открыть VIP-раздел магазина."""
    try:
        if query.data is None or query.from_user is None or query.message is None or query.bot is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        origin = _origin_ok(parts[3]) if len(parts) > 3 else "f"
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        await _shop_push_ui(
            state,
            query,
            char,
            shop_service.format_vip_shop_html(char),
            shop_vip_keyboard(floor_key, origin),
            vip=True,
        )
        await query.answer()
    except Exception:
        logger.exception("shp:vip")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("shp:vbuy:"))
async def shop_vip_buy(query: CallbackQuery, session: AsyncSession) -> None:
    """Инициировать покупку VIP-товара за Telegram Stars (send_invoice)."""
    try:
        if query.data is None or query.from_user is None or query.message is None or query.bot is None:
            await query.answer()
            return
        parts = query.data.split(":")
        if len(parts) < 5:
            await query.answer()
            return
        floor_key = int(parts[2])
        good_key = parts[3]
        origin = _origin_ok(parts[4])

        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return

        good = shop_data.vip_good_by_key(good_key)
        if good is None or good.stars_price <= 0:
            await query.answer("Товар не найден.", show_alert=True)
            return

        vs = str(good.item_data.get("virtual_shop") or "")
        if vs == "vip_star_bonus":
            bid = str(good.item_data.get("vip_bonus_id") or "").strip()
            if not bid:
                await query.answer("Ошибка товара.", show_alert=True)
                return
            if shop_service.vip_bonus_owned(char, bid):
                await query.answer("Этот набор уже куплен.", show_alert=True)
                return
            payload = f"vipbonus:{bid}:{query.from_user.id}"
        else:
            pk = str(good.item_data.get("portrait_key", ""))
            from services.home_service import has_portrait_unlock
            if not pk:
                await query.answer("Товар не поддерживается.", show_alert=True)
                return
            if has_portrait_unlock(char, pk):
                await query.answer("Этот облик уже куплен.", show_alert=True)
                return
            payload = f"portrait:{pk}:{query.from_user.id}"

        # Отправляем инвойс — Telegram Stars (currency="XTR")
        await query.bot.send_invoice(
            chat_id=query.message.chat.id,
            title=good.name,
            description=good.blurb,
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label=good.name, amount=good.stars_price)],
        )
        await query.answer()
    except Exception:
        logger.exception("shp:vbuy")
        await query.answer("Ошибка при создании счёта.", show_alert=True)


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery) -> None:
    """Подтвердить предварительный чек-аут для Stars-покупок."""
    try:
        payload = pre_checkout_query.invoice_payload
        # Проверяем формат полезной нагрузки: portrait:<key>:<user_id>
        if payload.startswith("portrait:") or payload.startswith("vipbonus:"):
            await pre_checkout_query.answer(ok=True)
            return
        if payload.startswith("stickerspin:"):
            parts = payload.split(":")
            if len(parts) < 2 or not parts[1].isdigit():
                await pre_checkout_query.answer(ok=False, error_message="Некорректный счёт.")
                return
            if int(parts[1]) != pre_checkout_query.from_user.id:
                await pre_checkout_query.answer(ok=False, error_message="Несовпадение пользователя.")
                return
            exp = int(getattr(settings, "STICKER_GACHA_STARS_PULL", 0) or 0)
            if exp <= 0:
                await pre_checkout_query.answer(ok=False, error_message="Товар недоступен.")
                return
            if (
                pre_checkout_query.currency != "XTR"
                or int(pre_checkout_query.total_amount) != exp
            ):
                await pre_checkout_query.answer(ok=False, error_message="Неверная сумма.")
                return
            await pre_checkout_query.answer(ok=True)
            return
        await pre_checkout_query.answer(ok=False, error_message="Неизвестный товар.")
    except Exception:
        logger.exception("pre_checkout")
        await pre_checkout_query.answer(ok=False, error_message="Ошибка на сервере.")


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, session: AsyncSession) -> None:
    """Применить покупку после успешной оплаты Stars."""
    try:
        if message.successful_payment is None or message.from_user is None:
            return

        payload = message.successful_payment.invoice_payload
        stars = message.successful_payment.total_amount
        currency = message.successful_payment.currency

        if payload.startswith("portrait:"):
            parts = payload.split(":")
            if len(parts) < 3:
                return
            portrait_key = parts[1]
            expected_uid = int(parts[2]) if parts[2].isdigit() else -1

            if message.from_user.id != expected_uid:
                await message.answer("⚠️ Ошибка: несоответствие пользователя.")
                return

            char = await _load_char(session, message.from_user.id)
            if char is None:
                await message.answer("⚠️ Персонаж не найден.")
                return

            ok, result_msg = shop_service.apply_stars_portrait_unlock(char, portrait_key)
            await session.flush()

            if ok:
                await message.answer(
                    f"✅ Оплата прошла! −{stars} ⭐\n{result_msg}",
                    parse_mode=ParseMode.HTML,
                )
            else:
                # Уже куплен — деньги вернёт Telegram автоматически (refund), но сообщим игроку
                await message.answer(
                    f"ℹ️ {result_msg}\n<i>Telegram вернёт {stars} ⭐ на счёт.</i>",
                    parse_mode=ParseMode.HTML,
                )
                # Возврат Stars
                try:
                    await message.bot.refund_star_payment(
                        user_id=message.from_user.id,
                        telegram_payment_charge_id=message.successful_payment.telegram_payment_charge_id,
                    )
                except Exception:
                    logger.warning("Stars refund failed for already-owned portrait")
            return

        if payload.startswith("vipbonus:"):
            parts = payload.split(":")
            if len(parts) < 3:
                return
            bonus_id = parts[1]
            expected_uid = int(parts[2]) if parts[2].isdigit() else -1

            if message.from_user.id != expected_uid:
                await message.answer("⚠️ Ошибка: несоответствие пользователя.")
                return

            char = await _load_char(session, message.from_user.id)
            if char is None:
                await message.answer("⚠️ Персонаж не найден.")
                return

            ok, result_msg = shop_service.apply_stars_vip_bonus_unlock(char, bonus_id)
            await session.commit()

            if ok:
                await message.answer(
                    f"✅ Оплата прошла! −{stars} ⭐\n{result_msg}",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await message.answer(
                    f"ℹ️ {result_msg}\n<i>Telegram вернёт {stars} ⭐ на счёт.</i>",
                    parse_mode=ParseMode.HTML,
                )
                try:
                    await message.bot.refund_star_payment(
                        user_id=message.from_user.id,
                        telegram_payment_charge_id=message.successful_payment.telegram_payment_charge_id,
                    )
                except Exception:
                    logger.warning("Stars refund failed for already-owned vip bonus")
            return

        if payload.startswith("stickerspin:"):
            parts = payload.split(":")
            if len(parts) < 2 or not parts[1].isdigit():
                return
            expected_uid = int(parts[1])
            if message.from_user.id != expected_uid:
                await message.answer("⚠️ Ошибка: несоответствие пользователя.")
                return
            exp = int(getattr(settings, "STICKER_GACHA_STARS_PULL", 0) or 0)
            if exp <= 0 or stars != exp or currency != "XTR":
                await message.answer("⚠️ Неверная сумма или валюта.")
                return
            char = await _load_char(session, message.from_user.id)
            if char is None:
                await message.answer("⚠️ Персонаж не найден.")
                try:
                    await message.bot.refund_star_payment(
                        user_id=message.from_user.id,
                        telegram_payment_charge_id=message.successful_payment.telegram_payment_charge_id,
                    )
                except Exception:
                    logger.warning("Stars refund failed stickerspin no char")
                return
            await character_repo.lock_character_row(session, char.id)
            from services import sticker_duel_service

            ok, result_msg, sid, src_floor = sticker_duel_service.apply_sticker_gacha_paid_spin_slot_only(char)
            await session.commit()
            if not ok:
                await message.answer(
                    f"ℹ️ {result_msg}\n<i>Telegram вернёт {stars} ⭐ на счёт.</i>",
                    parse_mode=ParseMode.HTML,
                )
                try:
                    await message.bot.refund_star_payment(
                        user_id=message.from_user.id,
                        telegram_payment_charge_id=message.successful_payment.telegram_payment_charge_id,
                    )
                except Exception:
                    logger.warning("Stars refund failed stickerspin spin fail")
                return
            await message.answer(
                f"✅ Оплата прошла! −{stars} ⭐\n{result_msg}",
                parse_mode=ParseMode.HTML,
            )
            await sticker_duel_service.send_card_art_after_pull(message.bot, message.chat.id, sid, src_floor)
            await sticker_duel_service.mirror_sticker_spin_to_gacha_chat(
                message.bot,
                session,
                char,
                msg_html=result_msg,
                sticker_id=sid,
            )
            return
    except Exception:
        logger.exception("successful_payment")
