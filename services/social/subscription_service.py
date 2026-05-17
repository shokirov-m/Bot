"""Проверка подписки на канал (ежедневка и бонусы)."""

from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from bot.i18n import t
from config import settings

_OK_STATUSES = frozenset({"creator", "administrator", "member", "restricted"})


def channel_chat_id() -> str:
    """@username или числовой id для get_chat_member."""
    u = (settings.REQUIRED_CHANNEL_USERNAME or "").strip()
    if not u:
        return "@trial_of_darkness"
    return u if u.startswith("@") else f"@{u}"


def channel_public_url() -> str:
    """Публичная ссылка t.me/<username> без @."""
    u = (settings.REQUIRED_CHANNEL_USERNAME or "trial_of_darkness").strip().lstrip("@")
    return f"https://t.me/{u}"


async def subscription_check(bot: Bot, telegram_user_id: int, *, locale: str) -> tuple[bool, str | None]:
    """
    (подписан, подсказка_html).
    При ошибке API Telegram — отдельное сообщение для игрока (бот не в канале и т.п.).
    """
    if settings.SKIP_CHANNEL_SUBSCRIPTION_CHECK:
        return True, None
    try:
        m = await bot.get_chat_member(chat_id=channel_chat_id(), user_id=telegram_user_id)
        ok = m.status in _OK_STATUSES
        return ok, None
    except TelegramBadRequest as e:
        logger.warning("get_chat_member TelegramBadRequest: {}", e)
        err = str(e).lower()
        if "chat not found" in err or "not enough rights" in err or "member not found" in err:
            return False, t(locale, "sub_err_channel_config")
        return False, t(locale, "sub_err_generic")
    except Exception:
        logger.exception("get_chat_member failed")
        return False, t(locale, "sub_err_generic")


async def user_is_subscribed(bot: Bot, telegram_user_id: int) -> bool:
    ok, _ = await subscription_check(bot, telegram_user_id, locale="ru")
    return ok
