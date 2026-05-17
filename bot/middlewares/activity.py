"""
Фиксация активности игрока (последний визит, оценка времени в игре) на каждом апдейте после авторизации.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from db.repository import character_repo, user_repo
from services.progression.activity_service import record_interaction


class ActivityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session = data.get("session")
        if isinstance(session, AsyncSession):
            fu = getattr(event, "from_user", None)
            if fu is not None:
                user = await user_repo.get_by_telegram_id(session, fu.id)
                if user is not None and not user.is_banned:
                    ch = await character_repo.get_by_user_id(session, int(user.id))
                    if ch is not None:
                        record_interaction(ch)

        return await handler(event, data)
