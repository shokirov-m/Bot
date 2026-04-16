"""
Доступ только для пользователей из таблицы users (после /start).
/start и вариант с @bot — без проверки (регистрация).
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from db.repository import user_repo

_WELCOME = "Добро пожаловать! Напиши /start для начала."


def _is_start_command(message: Message) -> bool:
    if not message.text:
        return False
    first = message.text.split(maxsplit=1)[0].lower()
    return first == "/start" or first.startswith("/start@")


class RegistrationAuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        if isinstance(event, Message) and _is_start_command(event):
            return await handler(event, data)

        session = data.get("session")
        if session is None:
            return await handler(event, data)

        fu = event.from_user
        if fu is None:
            return await handler(event, data)

        user = await user_repo.get_by_telegram_id(session, fu.id)
        if user is None:
            if isinstance(event, Message):
                await event.answer(_WELCOME)
            else:
                await event.answer("Сначала нажми /start.", show_alert=True)
            return None

        if user.is_banned:
            if isinstance(event, Message):
                await event.answer("Доступ запрещён.")
            else:
                await event.answer("Доступ запрещён.", show_alert=True)
            return None

        return await handler(event, data)
