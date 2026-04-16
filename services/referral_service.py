"""
Рефералка: ссылка в настройках, /start ref_<telegram_id>, награда пригласившему при 2 ур. приглашённого.
"""

from __future__ import annotations

import copy
import html
import re
from typing import TYPE_CHECKING

from aiogram.enums import ParseMode
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.models.user import User
from db.repository import character_repo, inventory_repo
from game.items import equipment as equip_mod
from services import character_service, title_service

if TYPE_CHECKING:
    from aiogram import Bot

REFERRAL_INVITER_XP = 100


def parse_referrer_telegram_id_from_start_text(text: str | None) -> int | None:
    """Из текста сообщения /start ref_123456789 — Telegram ID пригласившего."""
    raw = (text or "").strip()
    if not raw.lower().startswith("/start"):
        return None
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        return None
    arg = parts[1].strip()
    if not arg.startswith("ref_"):
        return None
    tail = arg[4:]
    if not re.fullmatch(r"\d{1,20}", tail):
        return None
    tid = int(tail)
    return tid if tid > 0 else None


def referral_start_payload(telegram_id: int) -> str:
    """Аргумент для t.me/bot?start=…"""
    return f"ref_{int(telegram_id)}"


def referral_bot_link(*, bot_username: str | None, telegram_id: int) -> str:
    from config import settings

    u = (bot_username or settings.BOT_USERNAME or "").strip().lstrip("@")
    return f"https://t.me/{u}?start={referral_start_payload(telegram_id)}"


async def resolve_bot_username_for_referral(bot: "Bot") -> str:
    """
    @username бота для реферальной ссылки.

    В aiogram 3 у объекта Bot часто нет атрибута .username — берём из get_me()
    или из settings.BOT_USERNAME.
    """
    from config import settings

    cached = getattr(bot, "username", None)
    if isinstance(cached, str) and cached.strip():
        return cached.strip().lstrip("@")
    try:
        me = await bot.get_me()
    except Exception:
        logger.exception("referral resolve_bot_username get_me")
        return (settings.BOT_USERNAME or "").strip().lstrip("@")
    u = (me.username or "").strip().lstrip("@")
    if u:
        return u
    return (settings.BOT_USERNAME or "").strip().lstrip("@")


async def bind_invitee_to_referrer(
    session: AsyncSession,
    *,
    invitee_user: User,
    referrer_telegram_id: int | None,
) -> None:
    """При создании героя: привязать приглашённого к users.id пригласившего (если валидно)."""
    if referrer_telegram_id is None:
        return
    if int(referrer_telegram_id) == int(invitee_user.telegram_id):
        return
    from db.repository import user_repo

    inviter = await user_repo.get_by_telegram_id(session, int(referrer_telegram_id))
    if inviter is None or int(inviter.id) == int(invitee_user.id):
        return
    invitee_user.referred_by_user_id = int(inviter.id)
    await session.flush()


async def try_reward_referrer_for_invitee_level_two(
    session: AsyncSession,
    invitee_char: Character,
    *,
    bot: Bot | None,
) -> None:
    """
    Если у персонажа только что стал уровень ≥ 2, а пользователь пришёл по рефке
    и награда ещё не выдана — дать пригласившему 2 предмета в сумку и +100 XP.
    """
    invitee_user = await session.get(User, int(invitee_char.user_id))
    if invitee_user is None:
        return
    if not invitee_user.referred_by_user_id:
        return
    if bool(invitee_user.referral_l2_payout_done):
        return
    if int(invitee_char.level) < 2:
        return

    inviter = await session.get(User, int(invitee_user.referred_by_user_id))
    if inviter is None or bool(inviter.is_banned):
        invitee_user.referral_l2_payout_done = True
        await session.flush()
        return

    inviter_char = await character_repo.get_by_user_id(session, int(inviter.id))
    if inviter_char is None:
        invitee_user.referral_l2_payout_done = True
        await session.flush()
        return

    added: list[str] = []
    for payload in equip_mod.referral_inviter_gear_payloads():
        free = await inventory_repo.first_free_bag_slot(session, int(inviter_char.id))
        if free is None:
            break
        await inventory_repo.add_bag_item(
            session,
            int(inviter_char.id),
            copy.deepcopy(payload),
            bag_slot=free,
        )
        added.append(str(payload.get("name", "Предмет")))

    character_service.add_experience(inviter_char, REFERRAL_INVITER_XP)
    title_service.refresh_unlocks(inviter_char)

    invitee_user.referral_l2_payout_done = True
    await session.flush()

    if bot is None:
        return
    invitee_n = html.escape(invitee_char.display_name)
    inviter_n = html.escape(inviter_char.display_name)
    if added:
        loot = ", ".join(html.escape(n) for n in added)
        loot_line = f" и в сумку: <b>{loot}</b>"
    else:
        loot_line = " (в сумке не было двух свободных ячеек — только опыт)."
    try:
        await bot.send_message(
            int(inviter.telegram_id),
            f"🎁 <b>Реферал дошёл до 2 уровня!</b>\n"
            f"Игрок <b>{invitee_n}</b>, которого ты привёл по ссылке, получил <b>2 уровень</b>.\n"
            f"Тебе: <b>+{REFERRAL_INVITER_XP}</b> опыта{loot_line}\n"
            f"<i>Твой герой <b>{inviter_n}</b> — сейчас ур. {int(inviter_char.level)}.</i>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("referral reward notify failed")
