"""Строки прогресса по этажам (посещения, боссы)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.floor_progress import FloorProgress


async def ensure_floor_row(
    session: AsyncSession,
    character_id: int,
    floor_number: int,
) -> FloorProgress:
    """Создать строку для пары персонаж–этаж, если ещё нет."""
    result = await session.execute(
        select(FloorProgress).where(
            FloorProgress.character_id == character_id,
            FloorProgress.floor_number == floor_number,
        ),
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = FloorProgress(
            character_id=character_id,
            floor_number=floor_number,
            visits=0,
            mini_boss_defeated=False,
            boss_defeated=False,
            secret_rooms_found=0,
            extra={},
        )
        session.add(row)
        await session.flush()
    return row
