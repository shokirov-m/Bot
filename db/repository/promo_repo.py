"""Промокоды: проверка и запись активации."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.promo_redemption import PromoRedemption


async def has_redeemed(session: AsyncSession, user_id: int, code_key: str) -> bool:
    r = await session.execute(
        select(func.count()).select_from(PromoRedemption).where(
            PromoRedemption.user_id == user_id,
            PromoRedemption.code_key == code_key,
        ),
    )
    return int(r.scalar_one() or 0) > 0


async def record_redemption(session: AsyncSession, user_id: int, code_key: str) -> None:
    session.add(PromoRedemption(user_id=user_id, code_key=code_key))
    await session.flush()
