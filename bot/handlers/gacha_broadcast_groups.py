"""
Группы: при добавлении бота в чат подписываем его на объявления о материалах 6★ из гачи дома.
При удалении бота — отписываем.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.types import ChatMemberUpdated
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from services import gacha_broadcast_service

router = Router(name="gacha_broadcast_groups")


def _is_bot(ev: ChatMemberUpdated, bot_id: int) -> bool:
    return int(ev.new_chat_member.user.id) == int(bot_id)


def _was_active(status: str | None) -> bool:
    return str(status or "") in ("member", "administrator", "creator", "restricted")


@router.my_chat_member()
async def on_bot_added_removed(ev: ChatMemberUpdated, session: AsyncSession) -> None:
    try:
        if ev.chat.type not in ("group", "supergroup"):
            return
        me = await ev.bot.get_me()
        if not _is_bot(ev, me.id):
            return

        old_st = ev.old_chat_member.status if ev.old_chat_member else "left"
        new_st = ev.new_chat_member.status

        was_in = _was_active(old_st)
        now_in = _was_active(new_st)

        cid = int(ev.chat.id)
        if now_in and not was_in:
            await gacha_broadcast_service.register_broadcast_chat(session, cid)
            logger.info("gacha_broadcast: подписан чат {}", cid)
        elif not now_in and was_in:
            await gacha_broadcast_service.unregister_broadcast_chat(session, cid)
            logger.info("gacha_broadcast: отписан чат {}", cid)
    except Exception:
        logger.exception("gacha_broadcast my_chat_member")
