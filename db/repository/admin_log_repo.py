"""Запись и выборка admin_logs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.admin_log import AdminLog


async def save_log(
    session: AsyncSession,
    *,
    actor_telegram_id: int,
    target_user_id: int | None,
    action: str,
    severity: str,
    message: str | None,
    payload: dict[str, Any],
) -> None:
    row = AdminLog(
        actor_telegram_id=actor_telegram_id,
        target_user_id=target_user_id,
        action=action,
        severity=severity,
        message=message,
        payload=payload,
    )
    session.add(row)
    await session.flush()


async def recent_high_severity(
    session: AsyncSession,
    *,
    limit: int = 10,
) -> list[AdminLog]:
    r = await session.execute(
        select(AdminLog)
        .where(AdminLog.severity.in_(("ALERT", "CRITICAL")))
        .order_by(AdminLog.created_at.desc())
        .limit(limit),
    )
    return list(r.scalars().all())


async def recent_all(
    session: AsyncSession,
    *,
    limit: int = 20,
) -> list[AdminLog]:
    """Последние записи любой важности (античит + действия админов)."""
    r = await session.execute(
        select(AdminLog).order_by(AdminLog.created_at.desc()).limit(limit),
    )
    return list(r.scalars().all())


async def count_alerts_since(
    session: AsyncSession,
    *,
    hours: int = 24,
    severities: tuple[str, ...] = ("ALERT", "CRITICAL"),
) -> tuple[int, int]:
    """(всего ALERT+CRITICAL, только CRITICAL) за последние hours часов."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    base = select(func.count()).select_from(AdminLog).where(
        AdminLog.severity.in_(severities),
        AdminLog.created_at >= since,
    )
    total = int((await session.execute(base)).scalar_one() or 0)
    crit_q = select(func.count()).select_from(AdminLog).where(
        AdminLog.severity == "CRITICAL",
        AdminLog.created_at >= since,
    )
    crit = int((await session.execute(crit_q)).scalar_one() or 0)
    return total, crit
