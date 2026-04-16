"""
Рефералка: ссылка в настройках, /start ref_<telegram_id>, награды пригласившему
(L2 приглашённого — редкие вещи + XP; пять приглашённых с 3+ ур. — эпическое ожерелье).
"""

from __future__ import annotations

import copy
import html
import re
from typing import TYPE_CHECKING

from aiogram.enums import ParseMode
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.models.user import User
from db.repository import character_repo, inventory_repo
from game.items import equipment as equip_mod
from services import character_service, title_service

if TYPE_CHECKING:
    from aiogram import Bot

REFERRAL_INVITER_XP = 200

# Пять разных приглашённых с уровнем героя ≥ 3 — пригласившему эпический амулет (ожерелье).
REFERRAL_FIVE_L3_MIN_LEVEL = 3
REFERRAL_FIVE_L3_INVITEE_COUNT = 5
REFERRAL_FIVE_L3_INVITER_STAT_POINTS = 5


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
    и награда ещё не выдана — дать пригласившему 2 предмета редкой редкости в сумку и +200 XP.
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


async def _count_invitees_at_least_level(
    session: AsyncSession,
    *,
    inviter_user_id: int,
    min_level: int,
) -> int:
    stmt = (
        select(func.count())
        .select_from(User)
        .join(Character, Character.user_id == User.id)
        .where(
            User.referred_by_user_id == int(inviter_user_id),
            User.is_banned.is_(False),
            Character.level >= int(min_level),
        )
    )
    res = await session.execute(stmt)
    return int(res.scalar_one() or 0)


async def try_reward_referrer_five_invitees_level_three(
    session: AsyncSession,
    invitee_char: Character,
    *,
    bot: Bot | None,
) -> None:
    """
    Если у приглашённого герой ≥ 3 ур., пригласивший ещё не получал награду
    и среди приглашённых уже ≥5 с уровнем ≥3 — выдать эпическое ожерелье в сумку.
    Вызывается при начислении опыта приглашённому с 3+ уровнем (в т.ч. повтор, если сумка была полна).
    """
    if int(invitee_char.level) < REFERRAL_FIVE_L3_MIN_LEVEL:
        return

    invitee_user = await session.get(User, int(invitee_char.user_id))
    if invitee_user is None or not invitee_user.referred_by_user_id:
        return

    inviter = await session.get(User, int(invitee_user.referred_by_user_id))
    if inviter is None or bool(inviter.is_banned):
        return
    if bool(inviter.referral_five_l3_necklace_done):
        return

    n = await _count_invitees_at_least_level(
        session,
        inviter_user_id=int(inviter.id),
        min_level=REFERRAL_FIVE_L3_MIN_LEVEL,
    )
    if n < REFERRAL_FIVE_L3_INVITEE_COUNT:
        return

    inviter_char = await character_repo.get_by_user_id(session, int(inviter.id))
    if inviter_char is None:
        return

    free = await inventory_repo.first_free_bag_slot(session, int(inviter_char.id))
    if free is None:
        if bot is not None:
            try:
                await bot.send_message(
                    int(inviter.telegram_id),
                    "🎁 <b>Реферальная награда!</b>\n"
                    "Пять приглашённых друзей достигли <b>3 уровня</b>, но в сумке "
                    "<b>нет свободной ячейки</b> для эпического ожерелья.\n"
                    "Освободи место — при следующем получении опыта любым из этих друзей награда придёт снова.",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                logger.exception("referral five-l3 bag full notify failed")
        return

    payload = equip_mod.referral_inviter_epic_necklace_payload()
    await inventory_repo.add_bag_item(
        session,
        int(inviter_char.id),
        copy.deepcopy(payload),
        bag_slot=free,
    )
    inviter.referral_five_l3_necklace_done = True
    inviter_char.unspent_stat_points = int(inviter_char.unspent_stat_points) + int(REFERRAL_FIVE_L3_INVITER_STAT_POINTS)
    title_service.refresh_unlocks(inviter_char)
    await session.flush()

    if bot is None:
        return
    inviter_n = html.escape(inviter_char.display_name)
    item_n = html.escape(str(payload.get("name", "Ожерелье")))
    try:
        await bot.send_message(
            int(inviter.telegram_id),
            f"🎁 <b>Пять друзей по ссылке — 3+ уровень!</b>\n"
            f"В сумку героя <b>{inviter_n}</b> добавлено эпическое снаряжение: <b>{item_n}</b>.\n"
            f"Бонус: <b>+{REFERRAL_FIVE_L3_INVITER_STAT_POINTS}</b> свободных очков характеристик.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("referral five-l3 reward notify failed")
