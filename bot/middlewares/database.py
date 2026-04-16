"""
Проброс async-сессии SQLAlchemy в data['session'] с commit/rollback.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_session_factory


class DbSessionMiddleware(BaseMiddleware):
    """Открывает сессию на время обработки апдейта."""

    def __init__(self) -> None:
        self._session_factory = get_session_factory()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self._session_factory() as session:  # type: AsyncSession
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
