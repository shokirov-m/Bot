"""Форматирование и отправка алертов администраторам."""

from __future__ import annotations

import html

from aiogram import Bot
from loguru import logger

from admin.anticheat import AnticheatAlert
from config import settings


async def send_alert_to_admins(bot: Bot, alert: AnticheatAlert) -> None:
    if not settings.ADMIN_IDS:
        return
    uname = html.escape(alert.username or "—")
    desc = html.escape(alert.description)
    body = (
        f"🛡️ <b>ANTICHEAT</b> <code>{html.escape(alert.severity)}</code>\n"
        f"Тип: <code>{html.escape(alert.check_type)}</code>\n"
        f"Игрок: <code>{alert.telegram_id}</code> @{uname}\n"
        f"Этаж / ур.: <b>{alert.floor}</b> / <b>{alert.level}</b>\n"
        f"{desc}\n"
        f"Значение: <code>{html.escape(str(alert.value))}</code> "
        f"(порог: <code>{html.escape(str(alert.expected_max))}</code>)"
    )
    for aid in settings.ADMIN_IDS:
        try:
            await bot.send_message(aid, body, parse_mode="HTML")
        except Exception:
            logger.warning("Не удалось отправить алерт админу {}", aid)
