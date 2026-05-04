"""Заказы мастерской (город, SQLite)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


async def create_order(
    session: AsyncSession,
    *,
    order_type: str,
    customer_char_id: int,
    recipe_id: str,
    qty: int,
    escrow_gold: int,
    deadline_at: str | None = None,
) -> int:
    now = _now_iso()
    r = await session.execute(
        text(
            """
            INSERT INTO workshop_orders
            (order_type, customer_char_id, recipe_id, qty, escrow_gold, status, deadline_at, created_at, updated_at)
            VALUES (:ot, :cid, :rid, :qty, :esc, 'posted', :deadline, :ca, :ua)
            """,
        ),
        {
            "ot": str(order_type)[:16],
            "cid": int(customer_char_id),
            "rid": str(recipe_id)[:64],
            "qty": max(1, int(qty)),
            "esc": int(escrow_gold),
            "deadline": deadline_at,
            "ca": now,
            "ua": now,
        },
    )
    await session.flush()
    rid = await session.execute(text("SELECT last_insert_rowid()"))
    return int(rid.scalar_one() or 0)


async def get_by_id(session: AsyncSession, order_id: int) -> dict[str, Any] | None:
    r = await session.execute(
        text("SELECT * FROM workshop_orders WHERE id = :id"),
        {"id": int(order_id)},
    )
    row = r.mappings().fetchone()
    return dict(row) if row is not None else None


async def list_posted(
    session: AsyncSession,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    r = await session.execute(
        text(
            "SELECT * FROM workshop_orders WHERE status = 'posted' "
            "ORDER BY id DESC LIMIT :lim",
        ),
        {"lim": int(limit)},
    )
    return [dict(x) for x in r.mappings().fetchall()]


async def list_for_customer(
    session: AsyncSession,
    customer_char_id: int,
) -> list[dict[str, Any]]:
    r = await session.execute(
        text(
            "SELECT * FROM workshop_orders WHERE customer_char_id = :c "
            "AND status IN ('posted','accepted') ORDER BY id DESC",
        ),
        {"c": int(customer_char_id)},
    )
    return [dict(x) for x in r.mappings().fetchall()]


async def list_for_crafter(
    session: AsyncSession,
    crafter_char_id: int,
) -> list[dict[str, Any]]:
    r = await session.execute(
        text(
            "SELECT * FROM workshop_orders WHERE crafter_char_id = :c "
            "AND status = 'accepted' ORDER BY id DESC",
        ),
        {"c": int(crafter_char_id)},
    )
    return [dict(x) for x in r.mappings().fetchall()]


async def set_accepted(
    session: AsyncSession,
    order_id: int,
    crafter_char_id: int,
) -> None:
    now = _now_iso()
    await session.execute(
        text(
            "UPDATE workshop_orders SET crafter_char_id = :cr, status = 'accepted', "
            "updated_at = :ua WHERE id = :id AND status = 'posted'",
        ),
        {"cr": int(crafter_char_id), "ua": now, "id": int(order_id)},
    )
    await session.flush()


async def set_completed(session: AsyncSession, order_id: int) -> None:
    now = _now_iso()
    await session.execute(
        text("UPDATE workshop_orders SET status = 'completed', updated_at = :ua WHERE id = :id"),
        {"ua": now, "id": int(order_id)},
    )
    await session.flush()


async def set_cancelled(session: AsyncSession, order_id: int) -> None:
    now = _now_iso()
    await session.execute(
        text("UPDATE workshop_orders SET status = 'cancelled', updated_at = :ua WHERE id = :id"),
        {"ua": now, "id": int(order_id)},
    )
    await session.flush()
