"""Обёртки экономики: аукцион с проверками (золото, лимит лотов)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import auction_repo
from game.economy import market


async def auction_create_lot(
    session: AsyncSession,
    char: Character,
    bag_slot: int,
    price: int,
) -> tuple[bool, str]:
    """Выставить лот: не более MAX активных лотов на продавца."""
    n = await auction_repo.count_active_by_seller(session, int(char.id))
    if n >= market.MAX_ACTIVE_LOTS_PER_SELLER:
        return (
            False,
            f"Не больше {market.MAX_ACTIVE_LOTS_PER_SELLER} активных лотов. Дождись окончания или снимай предмет после истечения.",
        )
    return await market.create_lot(session, char, bag_slot, price)


async def auction_place_bid(
    session: AsyncSession,
    char: Character,
    lot_id: int,
    amount: int,
) -> tuple[bool, str]:
    """Ставка с проверкой баланса до вызова ядра (ядро перепроверяет при торгах)."""
    amt = int(amount)
    if amt < 1:
        return False, "Сумма ставки должна быть положительной."
    if int(char.gold) < amt:
        return False, "Недостаточно золота."
    return await market.place_bid(session, char, lot_id, amt)


async def auction_finalize_lots(session: AsyncSession) -> int:
    """Для планировщика: закрыть просроченные лоты."""
    return await market.finalize_lots(session)
