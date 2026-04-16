"""
Кланы: создание, вступление по ID, карточка, ссылка на чат (базовый уровень).
"""

from __future__ import annotations

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db.repository import character_repo, user_repo
from services import clan_service

router = Router(name="clans")


def _tokens(message: Message) -> list[str]:
    raw = (message.text or "").strip()
    if not raw:
        return []
    parts = raw.split()
    cmd = parts[0].split("@", 1)[0].lower()
    if cmd not in ("/clan", "/клан"):
        return []
    return parts[1:]


@router.message(Command("clan", "клан"))
async def cmd_clan(message: Message, session: AsyncSession) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            await message.answer("Сначала /start.")
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Создай героя через /start.")
            return

        tok = _tokens(message)
        if not tok or tok[0].lower() in ("help", "?", "инфо", "info", "card"):
            body = await clan_service.format_clan_card_html(session, char)
            await message.answer(body, parse_mode=ParseMode.HTML)
            return

        sub = tok[0].lower()
        if sub == "create" and len(tok) >= 2:
            name = " ".join(tok[1:]).strip()
            ok, msg = await clan_service.try_create_clan(session, char, name)
            await message.answer(msg, parse_mode=ParseMode.HTML)
            return

        if sub == "join" and len(tok) >= 2:
            try:
                cid = int(tok[1])
            except ValueError:
                await message.answer(
                    "Укажи числовой ID клана: <code>/clan join 5</code>",
                    parse_mode=ParseMode.HTML,
                )
                return
            ok, msg = await clan_service.try_join_clan(session, char, cid)
            await message.answer(msg, parse_mode=ParseMode.HTML)
            return

        if sub == "chat" and len(tok) >= 2:
            url = " ".join(tok[1:]).strip()
            ok, msg = await clan_service.try_set_clan_chat(session, char, url)
            await message.answer(msg, parse_mode=ParseMode.HTML)
            return

        await message.answer("Неизвестная команда. См. <code>/clan</code>", parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("clan cmd")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
