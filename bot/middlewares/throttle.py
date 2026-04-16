"""Антиспам: не чаще одного апдейта на пользователя за MIN_INTERVAL_SEC."""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

MIN_INTERVAL_SEC = 0.4

_last_by_user: dict[int, float] = {}


class UserThrottleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        uid: int | None = None
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            uid = event.from_user.id

        if uid is None:
            return await handler(event, data)

        now = time.monotonic()
        prev = _last_by_user.get(uid, 0.0)
        if now - prev < MIN_INTERVAL_SEC:
            if isinstance(event, CallbackQuery):
                await event.answer("Не так быстро!", show_alert=True)
            elif isinstance(event, Message) and event.chat:
                await event.answer("Не так быстро!")
            return None

        _last_by_user[uid] = now
        return await handler(event, data)
