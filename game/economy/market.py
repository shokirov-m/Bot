"""
Игровой магазин (лоты): выставление, покупка по цене, личные предложения, финализация (комиссия 5 %).
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.auction_lot import AuctionLot
from db.models.character import Character
from db.repository import auction_repo, character_repo, inventory_repo
from game.balance import BAG_MAX_SLOT_INDEX

MAX_ACTIVE_LOTS_PER_SELLER = 5
LOT_DURATION_DAYS = 3
COMMISSION_RATE = 0.05
MAX_GOLD_BID = 9_999_999_999_999


def _expires_at_utc(expires_at: datetime) -> datetime:
    """SQLite/драйверы иногда отдают naive datetime — сравнение с UTC ломается."""
    dt = expires_at
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def min_next_bid_for_lot(lot: AuctionLot) -> int:
    if int(lot.current_bid) <= 0:
        return max(1, int(lot.start_price))
    return int(lot.current_bid) + 1


async def create_lot(
    session: AsyncSession,
    char: Character,
    bag_slot: int,
    price: int,
) -> tuple[bool, str]:
    """Снять предмет из сумки и создать лот. Лимит активных лотов — в economy_service."""
    if bag_slot < 0 or bag_slot > BAG_MAX_SLOT_INDEX:
        return False, "Некорректный слот сумки."
    p = int(price)
    if p < 1:
        return False, "Стартовая цена должна быть не меньше 1 золота."
    if p > MAX_GOLD_BID:
        return False, "Слишком большая цена."

    item = await inventory_repo.get_bag_item_at_slot(session, int(char.id), bag_slot)
    if item is None:
        return False, "В этой ячейке сумки нет предмета."

    data = copy.deepcopy(dict(item.item_data or {}))
    await inventory_repo.delete_inventory_item(session, item)

    exp = datetime.now(UTC) + timedelta(days=LOT_DURATION_DAYS)
    lot = AuctionLot(
        seller_char_id=int(char.id),
        item_data=data,
        start_price=p,
        current_bid=0,
        buyer_char_id=None,
        expires_at=exp,
        status="active",
    )
    session.add(lot)
    await session.flush()
    return True, f"Лот #{lot.id} · {LOT_DURATION_DAYS} дн. · цена {p} зол."


async def create_direct_offered_lot(
    session: AsyncSession,
    seller: Character,
    bag_slot: int,
    price: int,
    target: Character,
) -> tuple[bool, str, AuctionLot | None]:
    """
    Личное предложение: предмет из сумки, фиксированная цена, только target может купить.
    Не попадает в общий список лотов.
    """
    if int(seller.id) == int(target.id):
        return False, "Нельзя отправить предложение самому себе.", None
    if bag_slot < 0 or bag_slot > BAG_MAX_SLOT_INDEX:
        return False, "Некорректный слот сумки.", None
    p = int(price)
    if p < 1:
        return False, "Цена должна быть не меньше 1 золота.", None
    if p > MAX_GOLD_BID:
        return False, "Слишком большая цена.", None

    item = await inventory_repo.get_bag_item_at_slot(session, int(seller.id), bag_slot)
    if item is None:
        return False, "В этой ячейке сумки нет предмета.", None

    data = copy.deepcopy(dict(item.item_data or {}))
    await inventory_repo.delete_inventory_item(session, item)

    exp = datetime.now(UTC) + timedelta(days=LOT_DURATION_DAYS)
    lot = AuctionLot(
        seller_char_id=int(seller.id),
        item_data=data,
        start_price=p,
        current_bid=0,
        buyer_char_id=None,
        target_char_id=int(target.id),
        expires_at=exp,
        status="active",
    )
    session.add(lot)
    await session.flush()
    gid = int(target.game_id) if target.game_id is not None else 0
    return (
        True,
        f"Личное предложение #{lot.id} отправлено игроку (игровой ID {gid}) · цена {p} зол. · "
        f"{LOT_DURATION_DAYS} дн.",
        lot,
    )


async def place_bid(
    session: AsyncSession,
    char: Character,
    lot_id: int,
    amount: int,
) -> tuple[bool, str]:
    """Ставка: золото списывается; прошлому лидеру возвращается ставка."""
    amt = int(amount)
    if amt < 1:
        return False, "Сумма ставки некорректна."

    lot = await auction_repo.get_by_id(session, lot_id)
    if lot is None or lot.status != "active":
        return False, "Лот не найден или уже закрыт."
    if lot.target_char_id is not None:
        return False, "Это личное предложение — купи или откажись через кнопки в уведомлении."
    if datetime.now(UTC) >= _expires_at_utc(lot.expires_at):
        return False, "Время торгов по лоту истекло."
    if int(lot.seller_char_id) == int(char.id):
        return False, "Нельзя ставить на свой лот."

    need = min_next_bid_for_lot(lot)
    if amt < need:
        return False, f"Минимальная ставка: {need} зол."

    if int(char.gold) < amt:
        return False, "Недостаточно золота."

    if int(lot.buyer_char_id or 0) > 0 and int(lot.current_bid) > 0:
        prev = await character_repo.get_by_id(session, int(lot.buyer_char_id))
        if prev is not None:
            prev.gold = int(prev.gold) + int(lot.current_bid)

    char.gold = int(char.gold) - amt
    lot.current_bid = amt
    lot.buyer_char_id = int(char.id)
    await session.flush()
    return True, f"Ставка {amt} зол. · лот #{lot.id}."


async def buy_lot_now(
    session: AsyncSession,
    buyer: Character,
    lot_id: int,
) -> tuple[bool, str]:
    """Публичный лот: мгновенная покупка по цене start_price (без торгов)."""
    lot = await auction_repo.get_by_id(session, lot_id)
    if lot is None or lot.status != "active":
        return False, "Лот не найден или уже закрыт."
    if lot.target_char_id is not None:
        return False, "Это личное предложение — открой кнопки в личном сообщении."
    if datetime.now(UTC) >= _expires_at_utc(lot.expires_at):
        return False, "Лот истёк."
    if int(lot.seller_char_id) == int(buyer.id):
        return False, "Нельзя купить свой лот."
    price = int(lot.start_price)
    if int(buyer.gold) < price:
        return False, "Недостаточно золота."
    seller = await character_repo.get_by_id(session, int(lot.seller_char_id))
    if seller is None:
        return False, "Продавец не найден."
    free_b = await inventory_repo.first_free_bag_slot(session, int(buyer.id))
    if free_b is None:
        return False, "Освободи хотя бы одну ячейку сумки."
    buyer.gold = int(buyer.gold) - price
    payout = int(price * (1.0 - COMMISSION_RATE))
    seller.gold = int(seller.gold) + payout
    await inventory_repo.add_bag_item(
        session,
        int(buyer.id),
        copy.deepcopy(lot.item_data or {}),
        bag_slot=free_b,
    )
    lot.status = "sold"
    lot.current_bid = price
    lot.buyer_char_id = int(buyer.id)
    await session.flush()
    return True, f"Куплено за {price} зол. · лот #{lot.id}."


async def seller_cancel_lot(
    session: AsyncSession,
    char: Character,
    lot_id: int,
) -> tuple[bool, str]:
    """Снять свой лот, пока нет ставок; предмет возвращается в сумку."""
    lot = await auction_repo.get_by_id(session, lot_id)
    if lot is None or lot.status != "active":
        return False, "Лот не найден или уже закрыт."
    if int(lot.seller_char_id) != int(char.id):
        return False, "Это не твой лот."
    if datetime.now(UTC) >= _expires_at_utc(lot.expires_at):
        return False, "Срок лота истёк — дождись итога или обнови экран."
    if int(lot.current_bid) > 0 or lot.buyer_char_id is not None:
        return False, "Лот уже куплен или зарезервирован — снять нельзя."

    free = await inventory_repo.first_free_bag_slot(session, int(char.id))
    if free is None:
        return False, "В сумке нет свободной ячейки — освободи место и попробуй снова."

    await inventory_repo.add_bag_item(
        session,
        int(char.id),
        copy.deepcopy(lot.item_data or {}),
        bag_slot=free,
    )
    lot.status = "cancelled"
    await session.flush()
    return True, f"Лот #{lot.id} снят, предмет возвращён в сумку (ячейка {free})."


async def seller_reprice_lot(
    session: AsyncSession,
    char: Character,
    lot_id: int,
    new_price: int,
) -> tuple[bool, str]:
    """Изменить стартовую цену своего лота, пока нет ставок."""
    lot = await auction_repo.get_by_id(session, lot_id)
    if lot is None or lot.status != "active":
        return False, "Лот не найден или уже закрыт."
    if int(lot.seller_char_id) != int(char.id):
        return False, "Это не твой лот."
    if datetime.now(UTC) >= _expires_at_utc(lot.expires_at):
        return False, "Срок лота истёк."
    if int(lot.current_bid) > 0 or lot.buyer_char_id is not None:
        return False, "Лот уже куплен или зарезервирован — цену менять нельзя."

    p = int(new_price)
    if p < 1:
        return False, "Цена должна быть не меньше 1 золота."
    if p > MAX_GOLD_BID:
        return False, "Слишком большая цена."

    lot.start_price = p
    await session.flush()
    return True, f"Лот #{lot.id}: новая цена {p} зол."


async def accept_direct_offer(
    session: AsyncSession,
    buyer: Character,
    lot_id: int,
) -> tuple[bool, str]:
    """Покупка личного предложения по фиксированной цене start_price."""
    lot = await auction_repo.get_by_id(session, lot_id)
    if lot is None or lot.status != "active":
        return False, "Лот не найден или уже закрыт."
    if lot.target_char_id is None:
        return False, "Это не личное предложение."
    if int(lot.target_char_id) != int(buyer.id):
        return False, "Это предложение адресовано не тебе."
    if datetime.now(UTC) >= _expires_at_utc(lot.expires_at):
        return False, "Срок предложения истёк."
    price = int(lot.start_price)
    if int(buyer.gold) < price:
        return False, "Недостаточно золота."

    seller = await character_repo.get_by_id(session, int(lot.seller_char_id))
    if seller is None:
        return False, "Продавец не найден."

    free_b = await inventory_repo.first_free_bag_slot(session, int(buyer.id))
    if free_b is None:
        return False, "Освободи хотя бы одну ячейку сумки."

    buyer.gold = int(buyer.gold) - price
    payout = int(int(price) * (1.0 - COMMISSION_RATE))
    seller.gold = int(seller.gold) + payout
    await inventory_repo.add_bag_item(
        session,
        int(buyer.id),
        copy.deepcopy(lot.item_data or {}),
        bag_slot=free_b,
    )
    lot.status = "sold"
    lot.current_bid = price
    lot.buyer_char_id = int(buyer.id)
    await session.flush()
    return True, f"Куплено за {price} зол. Лот #{lot.id}."


async def decline_direct_offer(
    session: AsyncSession,
    buyer: Character,
    lot_id: int,
) -> tuple[bool, str]:
    """Отказ: предмет возвращается продавцу в сумку."""
    lot = await auction_repo.get_by_id(session, lot_id)
    if lot is None or lot.status != "active":
        return False, "Лот не найден или уже закрыт."
    if lot.target_char_id is None:
        return False, "Это не личное предложение."
    if int(lot.target_char_id) != int(buyer.id):
        return False, "Это предложение адресовано не тебе."
    if int(lot.current_bid) > 0 or lot.buyer_char_id is not None:
        return False, "Лот уже обработан."

    seller = await character_repo.get_by_id(session, int(lot.seller_char_id))
    if seller is None:
        lot.status = "cancelled"
        await session.flush()
        return False, "Продавец не найден — лот закрыт."

    free_s = await inventory_repo.first_free_bag_slot(session, int(seller.id))
    if free_s is None:
        return False, "У продавца нет места в сумке — попробуй позже или напиши продавцу."

    await inventory_repo.add_bag_item(
        session,
        int(seller.id),
        copy.deepcopy(lot.item_data or {}),
        bag_slot=free_s,
    )
    lot.status = "cancelled"
    lot.target_char_id = None
    await session.flush()
    return True, f"Отказ от лота #{lot.id}. Предмет возвращён продавцу."


async def finalize_lots(session: AsyncSession) -> int:
    """
    Закрыть просроченные активные лоты.
    Комиссия 5 % с выручки продавца; покупатель получает предмет в сумку.
    """
    lots = await auction_repo.list_expired_active(session)
    if not lots:
        return 0
    now = datetime.now(UTC)
    done = 0
    for lot in lots:
        seller = await character_repo.get_by_id(session, int(lot.seller_char_id))
        if seller is None:
            lot.status = "cancelled"
            done += 1
            continue

        has_sale = int(lot.current_bid) > 0 and lot.buyer_char_id is not None

        if has_sale:
            buyer = await character_repo.get_by_id(session, int(lot.buyer_char_id))
            if buyer is None:
                has_sale = False
            else:
                free_b = await inventory_repo.first_free_bag_slot(session, int(buyer.id))
                if free_b is None:
                    buyer.gold = int(buyer.gold) + int(lot.current_bid)
                    free_s = await inventory_repo.first_free_bag_slot(session, int(seller.id))
                    if free_s is None:
                        lot.expires_at = now + timedelta(days=1)
                        logger.warning(
                            "[AUCTION] buyer {} refunded, seller {} bag full — defer lot {}",
                            buyer.id,
                            seller.id,
                            lot.id,
                        )
                        continue
                    await inventory_repo.add_bag_item(
                        session,
                        int(seller.id),
                        copy.deepcopy(lot.item_data),
                        bag_slot=free_s,
                    )
                    lot.status = "expired"
                    lot.buyer_char_id = None
                    lot.current_bid = 0
                    done += 1
                    continue

                payout = int(int(lot.current_bid) * (1.0 - COMMISSION_RATE))
                seller.gold = int(seller.gold) + payout
                await inventory_repo.add_bag_item(
                    session,
                    int(buyer.id),
                    copy.deepcopy(lot.item_data),
                    bag_slot=free_b,
                )
                lot.status = "sold"
                done += 1
                continue

        free_s = await inventory_repo.first_free_bag_slot(session, int(seller.id))
        if free_s is None:
            lot.expires_at = now + timedelta(days=1)
            logger.warning("[AUCTION] seller {} bag full — defer lot {}", seller.id, lot.id)
            continue
        await inventory_repo.add_bag_item(
            session,
            int(seller.id),
            copy.deepcopy(lot.item_data),
            bag_slot=free_s,
        )
        lot.status = "expired"
        lot.buyer_char_id = None
        lot.current_bid = 0
        done += 1

    await session.flush()
    return done
