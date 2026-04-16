"""Уведомления о «первом на этаже N за сезон» (UTC-месяц)."""

from __future__ import annotations

from datetime import UTC, datetime

from aiogram import Bot
from aiogram.enums import ParseMode
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.app_global import AppGlobal
from db.models.character import Character
from db.models.user import User


async def notify_if_first_to_floor_milestone_this_season(
    session: AsyncSession,
    bot: Bot | None,
    character: Character,
    *,
    old_highest: int,
    new_highest: int,
) -> None:
    """
    Разовое личное сообщение: первый в сезоне (UTC-месяц), кто поднял рекорд highest_floor до N.
    """
    if bot is None or new_highest <= old_highest:
        return
    if new_highest < 2:
        return
    season = datetime.now(UTC).strftime("%Y-%m")
    row = await session.get(AppGlobal, 1)
    if row is None:
        row = AppGlobal(id=1, payload={})
        session.add(row)
        await session.flush()
    payload = dict(row.payload or {})
    root = payload.setdefault("season_floor_first", {})
    month_map: dict[str, int] = dict(root.get(season) or {})
    key = str(int(new_highest))
    if key in month_map:
        return
    month_map[key] = int(character.id)
    root[season] = month_map
    payload["season_floor_first"] = root
    row.payload = payload
    await session.flush()

    user = await session.get(User, int(character.user_id))
    if user is None:
        return
    try:
        await bot.send_message(
            int(user.telegram_id),
            f"🎉 <b>Рекорд сезона!</b>\n"
            f"Ты первый на этаже <b>{new_highest}</b> этого сезона (<b>{season}</b>, UTC)!",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("season record notify failed")
