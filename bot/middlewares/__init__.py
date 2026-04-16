"""Middleware: throttle, сессия БД, проверка регистрации. Фильтр админа — admin_check."""

from bot.middlewares.admin_check import IsAdmin
from bot.middlewares.auth import RegistrationAuthMiddleware
from bot.middlewares.database import DbSessionMiddleware
from bot.middlewares.throttle import UserThrottleMiddleware

__all__ = [
    "DbSessionMiddleware",
    "IsAdmin",
    "RegistrationAuthMiddleware",
    "UserThrottleMiddleware",
]
