"""
Запись метрик в game_events (не блокирует бой при ошибке записи).
"""

from __future__ import annotations

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db.repository import game_event_repo


async def record_event(
    session: AsyncSession,
    *,
    event_type: str,
    floor: int = 0,
    class_key: str = "",
) -> None:
    try:
        # SAVEPOINT: ошибка flush не переводит всю сессию в invalid (иначе ломается commit боя).
        async with session.begin_nested():
            await game_event_repo.insert_event(
                session,
                event_type=event_type,
                floor=floor,
                class_key=class_key,
            )
            await session.flush()
    except Exception:
        logger.exception("game_metrics record_event failed: {}", event_type)
