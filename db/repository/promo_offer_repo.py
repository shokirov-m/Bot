"""CRUD промокодов из БД (админка)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from sqlalchemy import delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.promo_offer import PromoOffer


def _now() -> datetime:
    return datetime.now(UTC)


async def get_by_code(session: AsyncSession, code_key: str) -> PromoOffer | None:
    ck = code_key.strip().upper()
    r = await session.execute(select(PromoOffer).where(PromoOffer.code_key == ck))
    return r.scalar_one_or_none()


def offer_is_valid_now(offer: PromoOffer, *, now: datetime | None = None) -> bool:
    if not offer.is_active:
        return False
    t = now or _now()
    if t < offer.valid_from:
        return False
    if offer.valid_until is not None and t > offer.valid_until:
        return False
    return True


async def try_take_one_use(session: AsyncSession, offer_id: int) -> bool:
    """
    Атомарно +1 к uses_count, если не исчерпан лимит и промо активно.
    Возвращает True, если строка обновлена.
    """
    cond_limit = or_(
        PromoOffer.max_uses.is_(None),
        PromoOffer.uses_count < PromoOffer.max_uses,
    )
    stmt = (
        update(PromoOffer)
        .where(
            PromoOffer.id == offer_id,
            PromoOffer.is_active.is_(True),
            cond_limit,
        )
        .values(uses_count=PromoOffer.uses_count + 1)
    )
    res = await session.execute(stmt)
    await session.flush()
    return res.rowcount > 0


async def create_offer(
    session: AsyncSession,
    *,
    code_key: str,
    gold: int,
    xp: int,
    rune_stones: int,
    max_uses: int | None,
    valid_days: int | None,
    created_by_telegram_id: int | None,
    note: str | None = None,
) -> PromoOffer:
    ck = code_key.strip().upper()
    now = _now()
    until: datetime | None = None
    if valid_days is not None and valid_days > 0:
        until = now + timedelta(days=int(valid_days))
    row = PromoOffer(
        code_key=ck,
        gold=max(0, int(gold)),
        xp=max(0, int(xp)),
        rune_stones=max(0, int(rune_stones)),
        max_uses=None if max_uses is None or int(max_uses) <= 0 else int(max_uses),
        uses_count=0,
        valid_from=now,
        valid_until=until,
        is_active=True,
        note=note,
        created_by_telegram_id=created_by_telegram_id,
    )
    session.add(row)
    await session.flush()
    return row


async def list_recent(session: AsyncSession, *, limit: int = 25) -> list[PromoOffer]:
    r = await session.execute(
        select(PromoOffer).order_by(desc(PromoOffer.created_at)).limit(limit),
    )
    return list(r.scalars().all())


async def set_active(session: AsyncSession, code_key: str, *, active: bool) -> bool:
    ck = code_key.strip().upper()
    res = await session.execute(
        update(PromoOffer)
        .where(PromoOffer.code_key == ck)
        .values(is_active=active),
    )
    await session.flush()
    return res.rowcount > 0


async def delete_by_code(session: AsyncSession, code_key: str) -> bool:
    ck = code_key.strip().upper()
    res = await session.execute(delete(PromoOffer).where(PromoOffer.code_key == ck))
    await session.flush()
    return res.rowcount > 0


async def count_offers(session: AsyncSession) -> int:
    r = await session.execute(select(func.count()).select_from(PromoOffer))
    return int(r.scalar_one() or 0)
