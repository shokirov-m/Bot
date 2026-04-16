"""Запросы к auction_lots."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import String as SAString
from sqlalchemy import func, not_, or_, select, type_coerce
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.auction_lot import AuctionLot
from game.items import item_categories


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


def _auction_kind_use_exprs():
    """
    Выражения для полей kind / use_tag в JSON item_data (SQLite).
    json_extract совместим с колонкой JSON в aiosqlite.
    """
    kind = type_coerce(
        func.json_extract(AuctionLot.item_data, "$.kind"),
        SAString,
    )
    use_tag = type_coerce(
        func.json_extract(AuctionLot.item_data, "$.use_tag"),
        SAString,
    )
    return kind, use_tag


def _auction_lot_category_clause(cat: str | None):
    """Фильтр по категории предмета (SQLite json_extract)."""
    if not cat or cat == item_categories.BAG_CAT_ALL:
        return None
    kind_expr, use_expr = _auction_kind_use_exprs()
    equip_tuple = tuple(sorted(item_categories.EQUIP_KINDS))
    eq_c = kind_expr.in_(equip_tuple)
    us_c = or_(
        kind_expr == "consumable",
        func.ifnull(use_expr, "") != "",
    )
    if cat == item_categories.BAG_CAT_EQUIP:
        return eq_c
    if cat == item_categories.BAG_CAT_USE:
        return us_c
    if cat == item_categories.BAG_CAT_OTHER:
        return not_(or_(eq_c, us_c))
    return None


async def list_active(
    session: AsyncSession,
    *,
    limit: int = 8,
    offset: int = 0,
    category: str | None = None,
) -> list[AuctionLot]:
    now = datetime.now(UTC)
    stmt = (
        select(AuctionLot)
        .where(
            AuctionLot.status == "active",
            AuctionLot.expires_at > now,
            AuctionLot.target_char_id.is_(None),
        )
        .order_by(AuctionLot.expires_at.asc())
    )
    extra = _auction_lot_category_clause(category)
    if extra is not None:
        stmt = stmt.where(extra)
    stmt = stmt.limit(limit).offset(offset)
    r = await session.execute(stmt)
    return list(r.scalars().all())


async def count_active_visible(session: AsyncSession, category: str | None = None) -> int:
    now = datetime.now(UTC)
    stmt = (
        select(func.count())
        .select_from(AuctionLot)
        .where(
            AuctionLot.status == "active",
            AuctionLot.expires_at > now,
            AuctionLot.target_char_id.is_(None),
        )
    )
    extra = _auction_lot_category_clause(category)
    if extra is not None:
        stmt = stmt.where(extra)
    r = await session.execute(stmt)
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
