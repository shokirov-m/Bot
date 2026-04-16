"""Вставка игровых событий для аналитики."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.game_event import GameEvent


async def insert_event(
    session: AsyncSession,
    *,
    event_type: str,
    floor: int = 0,
    class_key: str = "",
) -> None:
    session.add(
        GameEvent(
            event_type=str(event_type)[:32],
            floor=int(floor),
            class_key=str(class_key)[:32],
        ),
    )
