"""Запросы к auction_lots."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.auction_lot import AuctionLot


async def count_active_by_seller(session: AsyncSession, seller_char_id: int) -> int:
    r = await session.execute(
        select(func.count())
        .select_from(AuctionLot)
        .where(
            AuctionLot.seller_char_id == seller_char_id,
            AuctionLot.status == "active",
        ),
    )
    return int(r.scalar_one() or 0)


async def get_by_id(session: AsyncSession, lot_id: int) -> AuctionLot | None:
    r = await session.execute(select(AuctionLot).where(AuctionLot.id == lot_id))
    return r.scalar_one_or_none()


async def list_active(
    session: AsyncSession,
    *,
    limit: int = 8,
    offset: int = 0,
) -> list[AuctionLot]:
    now = datetime.now(UTC)
    r = await session.execute(
        select(AuctionLot)
        .where(
            AuctionLot.status == "active",
            AuctionLot.expires_at > now,
        )
        .order_by(AuctionLot.expires_at.asc())
        .limit(limit)
        .offset(offset),
    )
    return list(r.scalars().all())


async def count_active_visible(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    r = await session.execute(
        select(func.count())
        .select_from(AuctionLot)
        .where(
            AuctionLot.status == "active",
            AuctionLot.expires_at > now,
        ),
    )
    return int(r.scalar_one() or 0)


async def list_seller_lots(
    session: AsyncSession,
    seller_char_id: int,
    *,
    limit: int = 20,
) -> list[AuctionLot]:
    r = await session.execute(
        select(AuctionLot)
        .where(AuctionLot.seller_char_id == seller_char_id)
        .order_by(AuctionLot.id.desc())
        .limit(limit),
    )
    return list(r.scalars().all())


async def list_expired_active(session: AsyncSession) -> list[AuctionLot]:
    now = datetime.now(UTC)
    r = await session.execute(
        select(AuctionLot).where(
            AuctionLot.status == "active",
            AuctionLot.expires_at <= now,
        ),
    )
    return list(r.scalars().all())
