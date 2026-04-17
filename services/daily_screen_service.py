"""Текст экрана ежедневки + подписка (общий для /daily и меню)."""

from __future__ import annotations

import html

from aiogram import Bot

from bot.i18n import t
from db.models.character import Character
from services import daily_service
from services.subscription_service import channel_public_url, subscription_check


async def build_daily_body_html(
    bot: Bot,
    telegram_user_id: int,
    character: Character,
    *,
    locale: str,
    title_html: str | None = None,
) -> tuple[str, bool]:
    """
    Полный HTML текста и флаг «подписан».
    """
    del title_html  # заголовок внутри моноширинного блока
    subscribed, api_hint = await subscription_check(bot, telegram_user_id, locale=locale)
    box = daily_service.format_daily_box_html(character, locale=locale, subscribed=subscribed)
    name = t(locale, "channel_display_name")
    url = channel_public_url()
    link = f'<a href="{html.escape(url)}">{html.escape(name)}</a>'
    if api_hint:
        extra = "\n" + api_hint
    elif not subscribed:
        extra = "\n" + t(locale, "daily_sub_required", channel=html.escape(name), link=link)
    else:
        extra = "\n" + t(locale, "daily_sub_ok")
    return box + extra, subscribed
