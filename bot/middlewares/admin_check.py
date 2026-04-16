"""Фильтр: только Telegram ID из settings.ADMIN_IDS (для админ-хендлеров)."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import settings


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        uid = event.from_user.id if event.from_user else None
        return uid is not None and uid in settings.ADMIN_IDS
